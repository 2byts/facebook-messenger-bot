#fbchat_muqit/facbook/client.py

import asyncio
import json
import base64
import aiofiles

from pathlib import Path
from enum import Enum
from typing import List, Optional

from puremagic import from_string
from msgspec.json import Decoder


from ..state import State
from ..muqit import Mqtt
from ..logging.logger import FBChatLogger, get_logger 
from ..exception.errors import APIError, LoginError, ParsingError, ValidationError
from ..models.message import Mention
from .response_parser import PictureUploadResponse, Privacy, Audience, OverridenPrivacy, PrivacyRow,ResponsePostData, extract_privacy_data

from ..utils.utils import now, generate_uuid
from ..models.deltas.parser import MessageParser

class FBReaction(Enum):
    LIKE = "1635855486666999"
    LOVE = "1678524932434102"
    CARE = "613557422527858"
    HAHA = "115940658764963"
    WOW = "478547315650144"
    SAD = "908563459236466"
    ANGRY = "444813342392137"




def mention_to_dict(mentions: List[Mention]):
    return [
            {"entity": {"id": m.user_id }, "length": m.length, "offset": m.offset}
            for m in mentions
        ]



def post_attachments(picture_ids: Optional[List[str]] = None, video_ids: Optional[List[str]] = None): 
    if picture_ids and video_ids:
        return [{"photo": {"id": i}} for i in picture_ids] + [{ "video": {"audio_descriptions": None, "id": i, "notify_when_processed": True, "transcriptions": None, "was_created_via_unified_video_flow": None} } for i in video_ids]

    elif picture_ids:
        return [{"photo": {"id": i}} for i in picture_ids]
    elif video_ids:
        return [{ "video": {"audio_descriptions": None, "id": i, "notify_when_processed": True, "transcriptions": None, "was_created_via_unified_video_flow": None} } for i in video_ids]
    else:
        return []




class FacebookClient:
    """`FacebookClient` handles facebook posts, reaction, friend request etc. and for publishing post, commenting and reacting to Facebook posts."""
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._state: Optional[State] = None
        self._uid: str = ""
        self._name: str = ""
        self._parser = MessageParser(self.logger)
        self.logger: FBChatLogger = get_logger()
        self._mqtt: Optional[Mqtt] = None
        self._client_mutation_id = 0
        # response parser 
        self._privacyResponse_decoder = Decoder(type=OverridenPrivacy, strict=False)
        self._picture_upload_dec = Decoder(type=PictureUploadResponse, strict=False)
        self._post_create_dec = Decoder(type=ResponsePostData, strict=False) 
        # needed in headers for video upload
        self._origin = "https://www.facebook.com"
        self._referer = "https://www.facebook.com/"
        if self._state:
            self._origin = f"https://{self._state._host}"
            self._referer = f"https://{self._state._host}/"


    def get_mutation_id(self)-> str:
        m = self._client_mutation_id
        self._client_mutation_id += 1 
        return str(m)


    async def manage_friend_request(self, user_id: str, accept_request: bool = True):
        """Manage friend requests accept or reject a friend requests

        Args:
            user_id (str): The user's id you want to accept or reject the friend requests.
            accept_request (bool): Accepts the friend request if true else rejects it.
        """
        if not self._state:
            raise LoginError("Client is not logged in yet. `State` class is not initialised yet")
        ts = str(now())
        variables = {
            "input": {
                "click_correlation_id": ts,
                "click_proof_validation_result": "{\"validated\":true}",
                "friend_requester_id": user_id,   # The friend request sender
                "friending_channel": "FRIENDS_HOME_REQUESTS",
                "actor_id": self._uid,   # <-- your own ID (Client)
                "client_mutation_id": self.get_mutation_id(),  
                },
                "scale": 3,
                "refresh_num": 0,
            } 

        data = {
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "FriendingCometFriendRequestDeleteMutation",
            "server_timestamps": True,
            "doc_id":  "25003074442651692"
            }

        if accept_request:
            data["fb_api_req_friendly_name"] =  "FriendingCometFriendRequestConfirmMutation"
            data["doc_id"] =  "24205795295769853"
            variables["input"]["warn_ack"] = False
            variables["should_fix_banner"] = True 

        data["variables"] = json.dumps(variables)

        await self._state._post("https://www.facebook.com/api/graphql/", data=data, no_response=True)


    async def send_friend_request(self, user_ids: List[str]):
        """
        Send friend request to one or multiple users using their Id.

        Args:
            user_ids (List[str]): A list of user ids to send friend request.
        """
        data = {
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "FriendingCometFriendRequestSendMutation",
            "server_timestamps": True,  # Converted to proper boolean
            "variables": json.dumps({
                "input": {
                    "click_correlation_id": str(now()),
                    "click_proof_validation_result": "{\"validated\":true}",
                    "friend_requestee_ids": user_ids,
                    "friending_channel": "FRIENDS_HOME_MAIN",
                    "warn_ack_for_ids": [],
                    "actor_id": self._uid,
                    "client_mutation_id": self.get_mutation_id()
                    },
                "scale": 3
                }),
            "doc_id": "24974393785534352"
            }   
        if self._state:
            await self._state._post("/api/graphql/", data=data, no_response=True)
    
    async def unfriend(self, user_id: str):
        """Unfriend a friend using their Id.
        
        Args:
            user_id (str): Id of the User to unfriend.
        """
        
        data = {
                "fb_api_caller_class": "RelayModern",
                "fb_api_req_friendly_name": "FriendingCometUnfriendMutation",
                "server_timestamps": True,
                "variables": json.dumps({
                    "input": {
                        "source": "bd_profile_button",
                        "unfriended_user_id": user_id,
                        "actor_id": self._uid,
                        "client_mutation_id": self.get_mutation_id()
                        },
                    "scale": 3
                    }),
                "doc_id": "24028849793460009"
                }
        if self._state:
            await self._state._post("/api/graphql/", data=data, raw=True)

    async def cancel_friend_request(self, user_id: str):
        """Cancel a friend request that you sent using the requested to user Id.

        Args:
            user_id (str): The Id of the User you sent friend request to.
        """
        data = {
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "FriendingCometFriendRequestCancelMutation",
            "server_timestamps": True,
            "variables": json.dumps({
                "input": {
                    "cancelled_friend_requestee_id": user_id,
                    "click_correlation_id": str(now()),
                    "click_proof_validation_result": "{\"validated\":true}",
                    "friending_channel": "PROFILE_BUTTON",
                    "actor_id": self._uid,
                    "client_mutation_id": self.get_mutation_id()
                    },
                "scale": 3
                }),
            "doc_id": "24453541284254355"
            }

        if self._state:
            await self._state._post("/api/graphql/", data=data, raw=True)



    async def react_to_post(self, feedback_id: Optional[str] = None , post_id: Optional[int] = None, reaction: FBReaction = FBReaction.LOVE):
        """React to a post using post's feedback Id or Post Id

        Args:
            feedback_id (Optional[str]): The feedback Id of the post to react. 
            post_id (Optional[int]): The Id of post to react. (feedback_id or post_id one of them must be provided)
            reaction (FBReaction): The reaction to react with (LOVE, HAHA, SAD e.g.)
        """
        if not self._state:
            raise LoginError("Client is not logged in yet. `State` class is not initialised yet")
        if not feedback_id and not post_id:
            raise ValidationError("Either 'feedback_id' or 'post_id' must be provided to react to Facebook post.")

        if post_id:
            feedback_id = base64.b64encode(post_id.to_bytes((post_id.bit_length() + 7) // 8, byteorder='big')).decode('utf-8')

        data = {
            "lsd": self._state._lsd,
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "CometUFIFeedbackReactMutation",
            "server_timestamps": True,
            "variables": json.dumps({
                "input": {
                    "attribution_id_v2": f"CometHomeRoot.react,comet.home,tap_tabbar,{now()},420553,4748854339,,",
                    "feedback_id": feedback_id,
                    "feedback_reaction_id": reaction.value,
                    "feedback_source": "NEWS_FEED",
                    "is_tracking_encrypted": True,
                    "tracking": [],  # intentionally left empty
                    "session_id": generate_uuid(),
                    "actor_id": self._uid,
                    "client_mutation_id": self.get_mutation_id()
                    },
            "useDefaultActor": False,
            "__relay_internal__pv__CometUFIReactionsEnableShortNamerelayprovider": False,
            }),
            "doc_id": "24034997962776771"
        }

        await self._state._post("/api/graphql/", data=data, no_response=True)

    async def _pick_container_query(self, privacy_writer_id, privacy = None):
        data = {
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "CometPrivacySelectorPickerContainerQuery",
            "server_timestamps": True,
            "variables": json.dumps({
                "localPrivacyRow": privacy,
                "privacyWriteID": privacy_writer_id,  # long encoded string kept as-is
                "renderLocation": "COMET_COMPOSER",
                "scale": 3
                }),
            "doc_id": "24820345800985339",
        }
        if self._state:
            await self._state._post("/api/graphql/", data=data, no_response=True)



    async def _get_privacy_writer(self):
        if not self._state:
            raise LoginError("Client is not logged in yet. `State` class is not initialised yet")
        data = {
                "fb_api_caller_class": "RelayModern",
                "fb_api_req_friendly_name": "FeedComposerCometRootQuery",
                "server_timestamps": True,
                "variables": json.dumps({
                    "hasStory": False,
                    "isBizWeb": False,
                    "privacySelectorRenderLocation": "COMET_COMPOSER",
                    "profileID": self._uid,
                    "scale": 3,
                    "storyID": "",
                    "__relay_internal__pv__FeedComposerComet_isGenAILabelEnabledrelayprovider": False,
                    "__relay_internal__pv__CometUnifiedVideoCreation_showPrivacyMergereLayprovider": False,
                    "__relay_internal__pv__CometUGCPublicCreation_showComposerPublicAwarenessTooltiprelayprovider": False
                    }),
                "doc_id": "32319398104317803"                
            }
            
        r = await self._state._post("/api/graphql/", data=data, raw=True)
        # self.logger.info(f"{r[:700]}")
        # with open("privacy_writer.txt", "w") as f:
        #     f.write(r.decode())
        # may show errors in some accounts
        try:
            r = extract_privacy_data(r.decode())
        except Exception as e:
            raise ParsingError("Failed to parse graphql response while getting privacy writer Id to set audience type.", original_exception=e)
        return r



    async def _setPrivacyWriter(self, ids: List, privacyWriter: PrivacyRow, isAllow = False, isDeny = False, base_state = None)-> Privacy | None:
        if not self._state:
            raise LoginError("Client is not logged in yet. `State` class is not initialised yet")
        data = {
                "lsd": self._state._lsd,
                "fb_api_caller_class": "RelayModern",
                "fb_api_req_friendly_name": "refetchCometPrivacySelectorNonAutosavePickerQuery",
                "server_timestamps": True,
                "variables": json.dumps({
                    "localPrivacyRow": { 
                        "allow": ids if isAllow else [],
                        "base_state": base_state if base_state else privacyWriter.privacy_row_input.base_state.value,
                        "deny": ids if isDeny else [],
                        "tag_expansion_state":"UNSPECIFIED"
                        },
                    "privacyWriteID": privacyWriter.id,
                    "renderLocation":"COMET_COMPOSER",
                    "scale":3,
                    "tags": None
                    }),
                "doc_id": "24578653808469895",
                }

         
        r = await self._state._post("/api/graphql/", data=data, raw=True)
        if base_state:
            return
        r = self._privacyResponse_decoder.decode(r)
        return r.data.node.scope.selected_row_override


    async def _format_audience(self, specific_users, except_users, base_state):
        if specific_users and except_users:
            raise APIError("Provide 'specific_users' or 'except_users' only one at a time.")

        privacy_writer = await self._get_privacy_writer()
        await self._pick_container_query(privacy_writer.id)

        if base_state != privacy_writer.privacy_row_input.base_state.value and not specific_users and not except_users:
            await self._setPrivacyWriter([], privacy_writer, base_state=base_state)

        if specific_users:
            data = await self._setPrivacyWriter(specific_users, privacy_writer, isAllow=True)
            if data:
                specific_users = data.specific_users
                except_users = data.except_users 
                base_state = data.base_state.value

        elif except_users:
            data = await self._setPrivacyWriter(except_users, privacy_writer, isDeny=True)
            if data:
                specific_users = data.specific_users
                except_users = data.except_users 
                base_state = data.base_state.value

        form =  {
            "privacy": {
                "allow": specific_users or [],
                "base_state": base_state,
                "deny": except_users or [],
                "tag_expansion_state": "UNSPECIFIED",
                }
            }
        return form


    async def publish_post(self, text: str, image_paths: Optional[List[str]] = None, video_paths: Optional[List[str]] = None, tag_users: Optional[List[str]] = None,  specific_users: Optional[List[str]] = None, except_users: Optional[List[str]] = None, audience: Audience = Audience.PUBLIC, mentions: Optional[List[Mention]] = None) -> str:
        """Publish a post in facebook.

        Args:
            text (str): The text message you want to add in the post. 
            image_paths (Optional[str]): The Images you want to attach to the post. 
            video_paths (Optional[List[str]]): The video to attach to the post. 
            tag_users (Optional[str]): Tag users to the postu using their uid. 
            specific_users (Optional[str]): only show the post to specific users. 
            except_users (Optional[str]): Show the post except some users using their uid. 
            audience (Audience): The audience of the post can be FRIENDS, EVERYONE, ONLYME.
            mentions (Optional[List[Mention]]): The users you want to mention in the post. 

        Returns:
            str: If successfully published the post returns post's feedback Id (base64 encoded post id) or post Id.
        """
        if not self._state:
            raise LoginError("Client is not logged in yet. `State` class is not initialised yet")
        
        # Build attachments list
        attachments = []
        
        # Upload files if paths are provided
        uploaded_photo_ids = None
        uploaded_video_ids = None
        
        if image_paths:
            self.logger.info(f"Uploading {len(image_paths)} photos...")
            uploaded_photo_ids = await self.upload_photos(image_paths)
        
        if video_paths:
            self.logger.warning(f"Due to some issues attaching video to post is not supported at this moment. Skipping videos.")
            # self.logger.info(f"Uploading {len(video_paths)} videos...")
            # uploaded_video_ids = await self.upload_videos(video_paths)
        
        
        # Build attachments
        if uploaded_photo_ids or uploaded_video_ids:
            attachments = post_attachments(
                picture_ids=uploaded_photo_ids,
                video_ids=uploaded_video_ids
            )

        self.logger.info(f"attachments: {attachments}")
        self.logger.info("Now getting audience...")
        audience_data =  await self._format_audience(specific_users, except_users, audience.value)
        new_uuid = generate_uuid()
        variables = {
            "input": {
            "composer_entry_point": "inline_composer",
            "composer_source_surface": "newsfeed",
            "composer_type": "feed",
            "idempotence_token": f"{new_uuid}_FEED",
            "source": "WWW",
            "audience": audience_data,
            "message": {
                "ranges": mention_to_dict(mentions) if mentions else [],
                "text": text,
                },
            "inline_activities": [],
            "text_format_preset_id": "0",
            "publishing_flow": {
                "supported_flows": ["ASYNC_SILENT", "ASYNC_NOTIF", "FALLBACK"],
                },
            "attachments": attachments,
            "with_tags_ids": tag_users,
            "logging": {
                "composer_session_id": new_uuid,
                },
            "navigation_data": {
                "attribution_id_v2": f"CometHomeRoot.react,comet.home,via_cold_start,{now()},929297,4748854339,,"
                },
            "tracking": [None],
            "event_share_metadata": {
                "surface": "newsfeed",
                },
            "actor_id": self._uid,
            "client_mutation_id": "1",
            },
            "feedLocation": "NEWSFEED",
            "feedbackSource": 1,
            "focusCommentID": None,
            "gridMediaWidth": None,
            "groupID": None,
            "scale": 3,
            "privacySelectorRenderLocation": "COMET_STREAM",
            "checkPhotosToReelsUpsellEligibility": True,
            "renderLocation": "homepage_stream",
            "useDefaultActor": False,
            "inviteShortLinkKey": None,
            "isFeed": True,
            "isFundraiser": False,
            "isFunFactPost": False,
            "isGroup": False,
            "isEvent": False,
            "isTimeline": False,
            "isSocialLearning": False,
            "isPageNewsFeed": False,
            "isProfileReviews": False,
            "isWorkSharedDraft": False,
            "hashtag": None,
            "canUserManageOffers": False,
            "__relay_internal__pv__CometUFIShareActionMigrationrelayprovider": True,
            "__relay_internal__pv__GHLShouldChangeSponsoredDataFieldNamerelayprovider": True,
            "__relay_internal__pv__GHLShouldChangeAdIdFieldNamerelayprovider": True,
            "__relay_internal__pv__CometUFI_dedicated_comment_routable_dialog_gkrelayprovider": False,
            "__relay_internal__pv__CometUFICommentAvatarStickerAnimatedImagerelayprovider": False,
            "__relay_internal__pv__IsWorkUserrelayprovider": False,
            "__relay_internal__pv__CometUFIReactionsEnableShortNamerelayprovider": False,
            "__relay_internal__pv__FBReels_enable_view_dubbed_audio_type_gkrelayprovider": True,
            "__relay_internal__pv__FBReels_deprecate_short_form_video_context_gkrelayprovider": True,
            "__relay_internal__pv__FeedDeepDiveTopicPillThreadViewEnabledrelayprovider": False,
            "__relay_internal__pv__CometImmersivePhotoCanUserDisable3DMotionrelayprovider": False,
            "__relay_internal__pv__WorkCometIsEmployeeGKProviderrelayprovider": False,
            "__relay_internal__pv__IsMergQAPollsrelayprovider": False,
            "__relay_internal__pv__FBReels_enable_meta_ai_label_gkrelayprovider": True,
            "__relay_internal__pv__FBReelsMediaFooter_comet_enable_reels_ads_gkrelayprovider": True,
            "__relay_internal__pv__StoriesArmadilloReplyEnabledrelayprovider": True,
            "__relay_internal__pv__FBReelsIFUTileContent_reelsIFUPlayOnHoverrelayprovider": True,
            "__relay_internal__pv__GroupsCometGYSJFeedItemHeightrelayprovider": 150,
            "__relay_internal__pv__StoriesShouldIncludeFbNotesrelayprovider": False,
            "__relay_internal__pv__GHLShouldChangeSponsoredAuctionDistanceFieldNamerelayprovider": False,
            "__relay_internal__pv__GHLShouldUseSponsoredAuctionLabelFieldNameV1relayprovider": False,
            "__relay_internal__pv__GHLShouldUseSponsoredAuctionLabelFieldNameV2relayprovider": False,
        }

        data = {
            "lsd": self._state._lsd,
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "ComposerStoryCreateMutation",
            "server_timestamps": True,
            "variables": json.dumps(variables),  # This gets JSON stringified
            # "doc_id": "9137564299700449", 
            # "doc_id": "24309936402019358"
            # multiple doc ids were found 
            "doc_id": "24966185093062904"
            }
        headers = {
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "Origin": self._origin,
                "Referer":  self._referer
                }
        r = await self._state._post("/api/graphql/", data=data, raw=True, header_type="publish_post", headers=headers)
        try:
            r = self._post_create_dec.decode(r)
        except Exception as e:
            raise ParsingError("Failed to parse graphql response of post publishing. Coudn't get `feedback_id` or `post_id`", original_exception=e)
        if r.data.story_create.story_id:
            return r.data.story_create.story_id
        elif r.data.story_create.story:
            return r.data.story_create.story.id
        else: 
            return str(r.data.story_create.post_id)




    async def upload_photo(self, image_path: str)->str:
        """
        Upload a photo to Facebook and return the photo ID.
    
        Args:
            image_path (str): Path to the image file to upload
        
        Returns:
            str : Upload response containing photoID
        """
        if not self._state:
            raise LoginError("Client is not logged in yet. `State` class is not initialised yet")
        
        # Generate upload ID
        upload_id = f"jsc_c_{generate_uuid()[:8]}"
    
        # Read file
        file_path = Path(image_path)
        if not file_path.exists():
            raise ValidationError(f"File not found: {image_path}")
    
        async with aiofiles.open(file_path, 'rb') as f:
            file_data = await f.read()
            mimtype = from_string(file_data, True)

        data = {
                "lsd": self._state._lsd,
                "source": "8",
                "profile_id": self._uid,
                "waterfallxapp": "comet",
                "upload_id": upload_id
                }
        files = {"farr": (file_path.name, file_data, mimtype)}
    
        # Upload URL from your screenshot
        url = "https://upload.facebook.com/ajax/react_composer/attachments/photo/upload"
        headers = {
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-site",
                }
        
        response = await self._state._post(url, data=data, files=files, raw=True, headers=headers)
        response = self._picture_upload_dec.decode(response[response.index(b'{'):])
        return response.payload.photoID
        
        
    async def upload_photos(self, image_paths: List[str], max_concurrent: int = 5)->List[str]:
        """
        Upload multiple photos concurrently and return list of photo IDs.
        
        Args:
            image_paths (List[str]): List of image file paths to upload
            max_concurrent (int): Maximum number of concurrent uploads (default: 5)
            
        Returns:
            List[str]: List of successfully uploaded photo IDs (preserves order)
        """

        semaphore = asyncio.Semaphore(max_concurrent)
        async def upload_with_semaphore(path: str, index: int)-> str:
            """Upload with semaphore and return (index, photo_id)"""
            async with semaphore:
                self.logger.info(f"Uploading {index + 1}/{len(image_paths)}: {path}")
                photo_id = await self.upload_photo(path)
                return photo_id

        # Create tasks for all uploads
        tasks = [
            upload_with_semaphore(path, idx) 
            for idx, path in enumerate(image_paths)
        ]
        # Wait for all uploads to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        photo_ids = []
        errors = []
        
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Upload task failed with exception: {result}")
                errors.append(result)
            elif result is not None:  # (index, photo_id)
                photo_ids.append(result)
            else:
                errors.append(f"Upload failed for index {result[0]}")
        
        # Sort by original index to maintain order
     
        self.logger.info(f"Upload complete: {len(photo_ids)}/{len(image_paths)} successful")
        
        if errors:
            self.logger.warning(f"Encountered {len(errors)} errors during upload")
        
        return photo_ids

    # # ================= Video =============== s 
    #
    #
    # async def _get_video_upload_config(self) -> dict:
    #     """Get video uploader configuration."""
    #     if not self._state:
    #         raise LoginError("Client is not logged in yet.")
    #
    #     data = {
    #         "fb_api_caller_class": "RelayModern",
    #         "fb_api_req_friendly_name": "useCometVideoUploaderConfigQuery",
    #         "server_timestamps": True,
    #         "variables": json.dumps({
    #             "actorID": self._uid,
    #             "entryPoint": "feed",
    #             "targetID": ""
    #         }),
    #         "doc_id": "9734072893355148"
    #     }
    #
    #     response = await self._state._post(
    #         "/api/graphql/",
    #         data=data,
    #         raw=True
    #     )
    #
    #     data = json.loads(response.decode())
    #     config_str = data.get("data", {}).get("viewer", {}).get("comet_composer_video_uploader_config", "{}")
    #     config = json.loads(config_str)
    #
    #     return config
    #
    # async def _get_media_upload_config(self) -> dict:
    #     """Get media upload configuration."""
    #     if not self._state:
    #         raise LoginError("Client is not logged in yet.")
    #
    #
    #     data = {
    #         "fb_api_caller_class": "RelayModern",
    #         "fb_api_req_friendly_name": "MediaUploadFBDefaultServerConfigurationRetrieverQuery",
    #         "server_timestamps": True,
    #         "variables": json.dumps({
    #             "source_type": "newsfeed_composer"
    #         }),
    #         "doc_id": "24229633186643574"
    #     }
    #
    #     response = await self._state._post("/api/graphql/", data=data, raw=True) 
    #
    #     media = json.loads(response.decode())
    #     media = media["data"]["media_upload_config"]
    #     return {
    #             "start_uri": media["network_start"]["uri"],
    #             "receive_uri": media["network_receive"]["uri"]
    #             }
    #
    #
    #
    # async def _start_video_upload(self, file_size: int, config: dict) -> dict:
    #     """Start video upload session and get video_id."""
    #     if not self._state:
    #         raise LoginError("Client is not logged in yet.")
    #
    #     waterfall_id = generate_uuid().replace("-", "")
    #
    #     # the form data for start request
    #     form_data = {
    #         "waterfall_id": waterfall_id,
    #         "target_id": self._uid,
    #         "source": "newsfeed_composer",
    #         "composer_entry_point_ref": "feed",
    #         "supports_chunking": "true",
    #         "supports_file_api": "true",
    #         "file_size": str(file_size),
    #         "file_extension": "mp4",
    #         "partition_start_offset": "0",
    #         "partition_end_offset": str(file_size),
    #         "composer_dialog_version": "V2",
    #         "video_publisher_action_source": "",
    #         "lsd": self._state._lsd,
    #     }
    #     headers = {
    #             "Sec-Fetch-Mode": "cors",
    #             "Sec-Fetch-Site": "same-origin",
    #             "X-Fb-Lsd": self._state._lsd,
    #             "X-fb-video-waterfall_id": waterfall_id,
    #             }
    #
    #     # Start URL from config
    #     start_url = config.get("start_uri", f"https://{self._state._host}/ajax/video/upload/requests/start/")
    #
    #     response = await self._state._post(start_url + f"?av={self._uid}&__a=1", data=form_data, raw=True, headers=headers)
    #
    #     # Parse response
    #     # remove "for (;;);" by 9: to parse to json
    #     response = self._parser.decoder.decode(response[9:])
    #
    #     payload = response.get("payload", {})
    #     return {
    #         "video_id": payload.get("video_id"),
    #         "start_offset": payload.get("start_offset", 0),
    #         "end_offset": payload.get("end_offset", file_size),
    #         "skip_upload": payload.get("skip_upload", False),
    #         "waterfall_id": waterfall_id
    #     }
    #
    #
    #
    # async def _prepare_for_upload_chunk(self, upload_url):
    #     if not self._state:
    #         raise LoginError("Client is not logged in yet.")
    #     data = { "fb_dtsg_ag": self._state._fb_dtsg_ag, "jazoest": self._state._jazoest_async }
    #     await self._state._get(upload_url, params=data)
    #
    #
    # async def _get_request_access(self, upload_url, params):
    #     if not self._state:
    #         raise LoginError("Client is not logged in yet.")
    #     headers = {
    #             "Access-Control-Request-Headers": "composer_session_id,end_offset,id,offset,product_media_id,start_offset,x-entity-length,x-entity-name,x-entity-type,x-total-asset-size",
    #             "Access-Control-Request-Method": "POST",
    #             "Sec-Fetch-Dest": "empty",
    #             "Sec-Fetch-Mode": "cors",
    #             "Sec-Fetch-Site": "same-site",
    #             "Origin": self._origin,
    #             "Referer": self._referer
    #             }
    #
    #     await self._state._option(upload_url, params, headers)
    #
    #
    # async def _upload_video_chunk(
    #     self, 
    #     upload_url: str,
    #     video_id: str,
    #     video_data: Tuple[str, bytes, str],
    #     waterfall_id: str,
    #     start_offset: str,
    #     end_offset: str,
    #     video_size: str
    # ) -> str:
    #     if not self._state:
    #         raise LoginError("Client is not logged in yet.")
    #
    #     # From response 5: {"h":"1:MTAwMDA3MDgyMS5tcDQ=:video/mp4:..."}
    #     # Prepare headers for chunk upload
    #     fileData = {"": video_data}
    #     data = {"lsd": self._state._lsd, "__aaid": "0"}
    #     headers = {
    #             "Content-Length": video_size,
    #             "Composer_session_id": waterfall_id,
    #             "Product_media_id": video_id,
    #             "End_offset": str(end_offset),
    #             "Offset": str(start_offset),
    #             "Start_offset": str(start_offset),
    #             "Id": "undefined",
    #             "X-Entity-Length": video_size,
    #             "X-Entity-Name": "1000072022.mp4",
    #             "X-Entity-Type": "video/mp4",
    #             "X-Total-Asset-Size": video_size,
    #             "Origin": self._origin,
    #             "Referer":  self._referer,
    #             "Sec-Fetch-Mode": "cors",
    #             "Sec-Fetch-Site": "same-site",
    #             }
    #
    #     await self._get_request_access(upload_url, data)
    #
    #     response = await self._state._post(upload_url, data={}, params=data, files=fileData, raw=True, headers=headers) #type: ignore
    #     result = json.loads(response.decode())
    #     self.logger.debug(f"Received Upload Handler: {result}")
    #     upload_handle = result.get("h")  # This is the chunk upload handle 
    #
    #     return upload_handle
    #
    #
    # async def _finalize_video_upload(
    #     self,
    #     video_id: str,
    #     start_offset: str, 
    #     end_offset: str, 
    #     upload_handle: str,
    #     waterfall_id: str,
    #     config: dict,
    #     file_size: int
    # ) -> dict:
    #     """Finalize video upload after chunks are uploaded."""
    #     if not self._state:
    #         raise LoginError("Client is not logged in yet.")
    #
    #     # receive endpoint
    #     form_data = {
    #         "waterfall_id": waterfall_id,
    #         "target_id": self._uid,
    #         "video_id": video_id,
    #         "source": "newsfeed_composer",
    #         "composer_entry_point_ref": "feed",
    #         "supports_chunking": "true",
    #         "supports_upload_service": "true",
    #         "partition_start_offset": str(start_offset),
    #         "partition_end_offset": str(end_offset),
    #         "start_offset": str(start_offset),
    #         "end_offset": str(end_offset),
    #         "upload_speed": "741605.047318612",  # Calculate based on actual speed
    #         "fbuploader_video_file_chunk": upload_handle,
    #         "composer_dialog_version": "V2",
    #         "lsd": self._state._lsd,
    #     }
    #     headers = {
    #             "X-Fb-Lsd": self._state._lsd,
    #             "X-fb-video-waterfall_id": waterfall_id,
    #             "Sec-Fetch-Mode": "cors",
    #             "Sec-Fetch-Site": "same-origin",
    #             }
    #
    #     receive_url = config.get("receive_uri", f"https://{self._state._host}/ajax/video/upload/requests/receive/")
    #
    #     response = await self._state._post(receive_url + f"?av={self._uid}&__a=1", data=form_data, raw=True, headers=headers)
    #
    #     # remove "for (;;);"
    #     print("res: ", response)
    #     response = self._parser.decoder.decode(response[9:])
    #     return response.get("payload", {})
    #
    #
    # async def upload_video(self, video_path: str) -> str:
    #     """
    #     Upload a video file to Facebook and return the video ID.
    #
    #     Args:
    #         video_path (str): Path to the video file to upload
    #
    #     Returns:
    #         Optional[int]: Video ID if successful, None if failed
    #     """
    #     if not self._state:
    #         raise LoginError("Client is not logged in yet.")
    #
    #     try:
    #         # Validate file
    #         file_path = Path(video_path)
    #         if not file_path.exists():
    #             raise FBChatError(f"Video file not found: {video_path}")
    #         print("giving path")
    #         file_size = os.path.getsize(file_path)
    #         print("done getting path file size")
    #
    #         # Step 1: Get upload configurations
    #         self.logger.debug("Getting upload configurations...")
    #         video_config = await self._get_video_upload_config()
    #         media_config = await self._get_media_upload_config()
    #
    #         # Step 2: Start upload session
    #         start_result = await self._start_video_upload(file_size, media_config)
    #         video_id = start_result["video_id"]
    #         waterfall_id = start_result["waterfall_id"]
    #
    #         if start_result.get("skip_upload"):
    #             self.logger.info(f"Video already exists, skipping upload. Video ID: {video_id}")
    #             return str(video_id)
    #
    #         self.logger.info(f"Upload session started. Video ID: {video_id}")
    #
    #         # Step 3: Read and upload video file
    #         self.logger.debug("Uploading video data...")
    #
    #         async with aiofiles.open(file_path, 'rb') as f:
    #             video_data = await f.read()
    #             self.logger.info(f"video_data type is: {type(video_data)}")
    #
    #         start_offset = start_result["start_offset"]
    #         end_offset = start_result["end_offset"]
    #
    #         # Resumable upload endpoint
    #         service_name = video_config.get("resumable_service_name", "rupload")
    #         service_domain = video_config.get("resumable_service_domain", "facebook.com")
    #         upload_uuid = generate_uuid().replace("-", "")
    #
    #
    #         # Upload host
    #         upload_url = f"https://{service_name}.{service_domain}/fb_video/{upload_uuid}-{start_offset}-{end_offset}"
    #
    #         await self._prepare_for_upload_chunk(upload_url)
    #
    #         upload_handle = await self._upload_video_chunk(
    #             upload_url,
    #             video_id=video_id,
    #             video_data=(os.path.basename(file_path), video_data, self._state._magic.from_file(file_path)),
    #             waterfall_id=waterfall_id,
    #             start_offset=start_offset,
    #             end_offset=end_offset,
    #             video_size=str(file_size)
    #         )
    #
    #         self.logger.info(f"Video data uploaded. Handle: {upload_handle}...")
    #
    #         # Step 4: Finalize upload
    #         self.logger.info("Finalizing upload...")
    #         finalize_result = await self._finalize_video_upload(
    #             video_id=video_id,
    #             start_offset=start_offset, 
    #             end_offset=end_offset,
    #             upload_handle=upload_handle,
    #             waterfall_id=waterfall_id,
    #             config=media_config,
    #             file_size=file_size
    #         )
    #         self.logger.debug(f"Finalized result: {finalize_result}")
    #
    #         self.logger.info(f"Video upload completed successfully. Video ID: {video_id}")
    #
    #         return str(video_id)
    #
    #     except Exception as e:
    #         raise FBChatError(f"Error uploading video {video_path}: {str(e)}")
    #
    # async def upload_videos( 
    #     self, 
    #     video_paths: List[str], 
    #     max_concurrent: int = 2  # Videos are larger, use fewer concurrent uploads
    # ) -> List[str]:
    #     """
    #     Upload multiple videos concurrently and return list of video IDs.
    #
    #     Args:
    #         video_paths (List[str]): List of video file paths to upload
    #         max_concurrent (int): Maximum number of concurrent uploads (default: 2)
    #
    #     Returns:
    #         List[int]: List of successfully uploaded video IDs
    #     """
    #     if not video_paths:
    #         return []
    #
    #     self.logger.info(f"Starting upload of {len(video_paths)} videos")
    #
    #     # Create semaphore to limit concurrent uploads
    #     semaphore = asyncio.Semaphore(max_concurrent)
    #
    #     async def upload_with_semaphore(path: str, index: int) -> str:
    #         """Upload with semaphore and return (index, video_id)"""
    #         async with semaphore:
    #             self.logger.info(f"Uploading video {index + 1}/{len(video_paths)}: {path}")
    #             video_id = await self.upload_video(path)
    #             return str(video_id)
    #
    #     # tasks for all uploads
    #     tasks = [
    #         upload_with_semaphore(path, idx) 
    #         for idx, path in enumerate(video_paths)
    #     ]
    #
    #     # Wait for all uploads to complete
    #     results = await asyncio.gather(*tasks, return_exceptions=True)
    #
    #     # Process results
    #     video_ids = []
    #     errors = []
    #
    #     for result in results:
    #         if isinstance(result, Exception):
    #             self.logger.error(f"Video upload task failed: {result}")
    #             errors.append(result)
    #         elif result is not None:
    #             video_ids.append(result)
    #         else:
    #             errors.append(f"Upload failed for index {result}")
    #
    #     # Sort by original index
    #
    #     self.logger.info(f"Video upload complete: {len(video_ids)}/{len(video_paths)} successful")
    #
    #     return video_ids




