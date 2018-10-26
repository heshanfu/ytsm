import logging
from typing import Callable, Union, Any, Optional
import os

from django.contrib.auth.models import User
from django.contrib.auth.models import User
from django.db import models
from django.db.models.functions import Lower
from YtManagerApp.utils.youtube import YoutubeAPI, YoutubeChannelInfo, YoutubePlaylistInfo

# help_text = user shown text
# verbose_name = user shown name
# null = nullable, blank = user is allowed to set value to empty


class UserSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    mark_deleted_as_watched = models.BooleanField(
        null=True, blank=True,
        help_text='When a downloaded video is deleted from the system, it will be marked as \'watched\'.')

    delete_watched = models.BooleanField(
        null=True, blank=True,
        help_text='Videos marked as watched are automatically deleted.')

    auto_download = models.BooleanField(
        null=True, blank=True,
        help_text='Enables or disables automatic downloading.')

    download_global_limit = models.IntegerField(
        null=True, blank=True,
        help_text='Limits the total number of videos downloaded (-1 = no limit).')

    download_subscription_limit = models.IntegerField(
        null=True, blank=True,
        help_text='Limits the number of videos downloaded per subscription (-1 = no limit). '
                  ' This setting can be overriden for each individual subscription in the subscription edit dialog.')

    download_order = models.CharField(
        null=True, blank=True,
        max_length=100,
        help_text='The order in which videos will be downloaded.'
    )

    download_path = models.CharField(
        null=True, blank=True,
        max_length=1024,
        help_text='Path on the disk where downloaded videos are stored. '
                  ' You can use environment variables using syntax: <code>${env:...}</code>'
    )

    download_file_pattern = models.CharField(
        null=True, blank=True,
        max_length=1024,
        help_text='A pattern which describes how downloaded files are organized. Extensions are automatically appended.'
                  ' You can use the following fields, using the <code>${field}</code> syntax:'
                  ' channel, channel_id, playlist, playlist_id, playlist_index, title, id.'
                  ' Example: <code>${channel}/${playlist}/S01E${playlist_index} - ${title} [${id}]</code>')

    download_format = models.CharField(
        null=True, blank=True,
        max_length=256,
        help_text='Download format that will be passed to youtube-dl. '
                  ' See the <a href="https://github.com/rg3/youtube-dl/blob/master/README.md#format-selection">'
                  ' youtube-dl documentation</a> for more details.')

    download_subtitles = models.BooleanField(
        null=True, blank=True,
        help_text='Enable downloading subtitles for the videos.'
                  ' The flag is passed directly to youtube-dl. You can find more information'
                  ' <a href="https://github.com/rg3/youtube-dl/blob/master/README.md#subtitle-options">here</a>.')

    download_autogenerated_subtitles = models.BooleanField(
        null=True, blank=True,
        help_text='Enables downloading the automatically generated subtitle.'
                  ' The flag is passed directly to youtube-dl. You can find more information'
                  ' <a href="https://github.com/rg3/youtube-dl/blob/master/README.md#subtitle-options">here</a>.')

    download_subtitles_all = models.BooleanField(
        null=True, blank=True,
        help_text='If enabled, all the subtitles in all the available languages will be downloaded.'
                  ' The flag is passed directly to youtube-dl. You can find more information'
                  ' <a href="https://github.com/rg3/youtube-dl/blob/master/README.md#subtitle-options">here</a>.')

    download_subtitles_langs = models.CharField(
        null=True, blank=True,
        max_length=250,
        help_text='Comma separated list of languages for which subtitles will be downloaded.'
                  ' The flag is passed directly to youtube-dl. You can find more information'
                  ' <a href="https://github.com/rg3/youtube-dl/blob/master/README.md#subtitle-options">here</a>.')

    download_subtitles_format = models.CharField(
        null=True, blank=True,
        max_length=100,
        help_text='Subtitles format preference. Examples: srt/ass/best'
                  ' The flag is passed directly to youtube-dl. You can find more information'
                  ' <a href="https://github.com/rg3/youtube-dl/blob/master/README.md#subtitle-options">here</a>.')

    @staticmethod
    def find_by_user(user: User):
        result = UserSettings.objects.filter(user=user)
        if len(result) > 0:
            return result.first()
        return None

    def __str__(self):
        return str(self.user)

    def to_dict(self):
        ret = {}

        if self.mark_deleted_as_watched is not None:
            ret['MarkDeletedAsWatched'] = self.mark_deleted_as_watched
        if self.delete_watched is not None:
            ret['DeleteWatched'] = self.delete_watched
        if self.auto_download is not None:
            ret['AutoDownload'] = self.auto_download
        if self.download_global_limit is not None:
            ret['DownloadGlobalLimit'] = self.download_global_limit
        if self.download_subscription_limit is not None:
            ret['DownloadSubscriptionLimit'] = self.download_subscription_limit
        if self.download_order is not None:
            ret['DownloadOrder'] = self.download_order
        if self.download_path is not None:
            ret['DownloadPath'] = self.download_path
        if self.download_file_pattern is not None:
            ret['DownloadFilePattern'] = self.download_file_pattern
        if self.download_format is not None:
            ret['DownloadFormat'] = self.download_format
        if self.download_subtitles is not None:
            ret['DownloadSubtitles'] = self.download_subtitles
        if self.download_autogenerated_subtitles is not None:
            ret['DownloadAutogeneratedSubtitles'] = self.download_autogenerated_subtitles
        if self.download_subtitles_all is not None:
            ret['DownloadSubtitlesAll'] = self.download_subtitles_all
        if self.download_subtitles_langs is not None:
            ret['DownloadSubtitlesLangs'] = self.download_subtitles_langs
        if self.download_subtitles_format is not None:
            ret['DownloadSubtitlesFormat'] = self.download_subtitles_format

        return ret


class SubscriptionFolder(models.Model):
    name = models.CharField(null=False, max_length=250)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False, blank=False)

    class Meta:
        ordering = [Lower('parent__name'), Lower('name')]

    def __str__(self):
        s = ""
        current = self
        while current is not None:
            s = current.name + " > " + s
            current = current.parent
        return s[:-3]

    def delete_folder(self, keep_subscriptions: bool):
        if keep_subscriptions:

            def visit(node: Union["SubscriptionFolder", "Subscription"]):
                if isinstance(node, Subscription):
                    node.parent_folder = None
                    node.save()

            SubscriptionFolder.traverse(self.id, self.user, visit)

        self.delete()

    @staticmethod
    def traverse(root_folder_id: Optional[int],
                 user: User,
                 visit_func: Callable[[Union["SubscriptionFolder", "Subscription"]], Any]):

        data_collected = []

        def collect(data):
            if data is not None:
                data_collected.append(data)

        # Visit root
        if root_folder_id is not None:
            root_folder = SubscriptionFolder.objects.get(id=root_folder_id)
            collect(visit_func(root_folder))

        queue = [root_folder_id]
        visited = []

        while len(queue) > 0:
            folder_id = queue.pop()

            if folder_id in visited:
                logging.error('Found folder tree cycle for folder id %d.', folder_id)
                continue
            visited.append(folder_id)

            for folder in SubscriptionFolder.objects.filter(parent_id=folder_id, user=user).order_by(Lower('name')):
                collect(visit_func(folder))
                queue.append(folder.id)

            for subscription in Subscription.objects.filter(parent_folder_id=folder_id, user=user).order_by(Lower('name')):
                collect(visit_func(subscription))

        return data_collected


class Channel(models.Model):
    channel_id = models.TextField(null=False, unique=True)
    username = models.TextField(null=True, unique=True)
    custom_url = models.TextField(null=True, unique=True)
    name = models.TextField()
    description = models.TextField()
    icon_default = models.TextField()
    icon_best = models.TextField()
    upload_playlist_id = models.TextField()

    def __str__(self):
        return self.name

    @staticmethod
    def find_by_channel_id(channel_id):
        result = Channel.objects.filter(channel_id=channel_id)
        if len(result) > 0:
            return result.first()
        return None

    @staticmethod
    def find_by_username(username):
        result = Channel.objects.filter(username=username)
        if len(result) > 0:
            return result.first()
        return None

    @staticmethod
    def find_by_custom_url(custom_url):
        result = Channel.objects.filter(custom_url=custom_url)
        if len(result) > 0:
            return result.first()
        return None

    def fill(self, yt_channel_info: YoutubeChannelInfo):
        self.channel_id = yt_channel_info.getId()
        self.custom_url = yt_channel_info.getCustomUrl()
        self.name = yt_channel_info.getTitle()
        self.description = yt_channel_info.getDescription()
        self.icon_default = yt_channel_info.getDefaultThumbnailUrl()
        self.icon_best = yt_channel_info.getBestThumbnailUrl()
        self.upload_playlist_id = yt_channel_info.getUploadsPlaylist()
        self.save()

    @staticmethod
    def get_or_create(url_type: str, url_id: str, yt_api: YoutubeAPI):
        channel: Channel = None
        info_channel: YoutubeChannelInfo = None

        if url_type == 'user':
            channel = Channel.find_by_username(url_id)
            if not channel:
                info_channel = yt_api.get_channel_info_by_username(url_id)
                channel = Channel.find_by_channel_id(info_channel.getId())

        elif url_type == 'channel_id':
            channel = Channel.find_by_channel_id(url_id)
            if not channel:
                info_channel = yt_api.get_channel_info(url_id)

        elif url_type == 'channel_custom':
            channel = Channel.find_by_custom_url(url_id)
            if not channel:
                found_channel_id = yt_api.search_channel(url_id)
                channel = Channel.find_by_channel_id(found_channel_id)
                if not channel:
                    info_channel = yt_api.get_channel_info(found_channel_id)

        # If we downloaded information about the channel, store information
        # about the channel here.
        if info_channel:
            if not channel:
                channel = Channel()
            if url_type == 'user':
                channel.username = url_id
            channel.fill(info_channel)

        return channel


class Subscription(models.Model):
    name = models.CharField(null=False, max_length=1024)
    parent_folder = models.ForeignKey(SubscriptionFolder, on_delete=models.CASCADE, null=True, blank=True)
    playlist_id = models.CharField(null=False, max_length=128)
    description = models.TextField()
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
    icon_default = models.CharField(max_length=1024)
    icon_best = models.CharField(max_length=1024)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # overrides
    auto_download = models.BooleanField(null=True, blank=True)
    download_limit = models.IntegerField(null=True, blank=True)
    download_order = models.CharField(null=True, blank=True, max_length=128)
    manager_delete_after_watched = models.BooleanField(null=True, blank=True)

    def fill_from_playlist(self, info_playlist: YoutubePlaylistInfo):
        self.name = info_playlist.getTitle()
        self.playlist_id = info_playlist.getId()
        self.description = info_playlist.getDescription()
        self.icon_default = info_playlist.getDefaultThumbnailUrl()
        self.icon_best = info_playlist.getBestThumbnailUrl()

    def copy_from_channel(self):
        # No point in storing info about the 'uploads from X' playlist
        self.name = self.channel.name
        self.playlist_id = self.channel.upload_playlist_id
        self.description = self.channel.description
        self.icon_default = self.channel.icon_default
        self.icon_best = self.channel.icon_best

    def fetch_from_url(self, url, yt_api: YoutubeAPI):
        url_type, url_id = yt_api.parse_channel_url(url)
        if url_type == 'playlist_id':
            info_playlist = yt_api.get_playlist_info(url_id)
            self.channel = Channel.get_or_create('channel_id', info_playlist.getChannelId(), yt_api)
            self.fill_from_playlist(info_playlist)
        else:
            self.channel = Channel.get_or_create(url_type, url_id, yt_api)
            self.copy_from_channel()

    def delete_subscription(self, keep_downloaded_videos: bool):
        self.delete()

    def __str__(self):
        return self.name


class Video(models.Model):
    video_id = models.TextField(null=False)
    name = models.TextField(null=False)
    description = models.TextField()
    watched = models.BooleanField(default=False, null=False)
    downloaded_path = models.TextField(null=True, blank=True)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    playlist_index = models.IntegerField(null=False)
    publish_date = models.DateTimeField(null=False)
    icon_default = models.TextField()
    icon_best = models.TextField()
    uploader_name = models.TextField(null=False)
    views = models.IntegerField(null=False, default=0)
    rating = models.FloatField(null=False, default=0.5)

    def mark_watched(self):
        self.watched = True
        self.save()
        if self.downloaded_path is not None:
            from YtManagerApp.appconfig import get_user_config
            from YtManagerApp.management.jobs.delete_video import schedule_delete_video
            from YtManagerApp.management.jobs.synchronize import schedule_synchronize_now_subscription

            user_cfg = get_user_config(self.subscription.user)
            if user_cfg.getboolean('user', 'DeleteWatched'):
                schedule_delete_video(self)
                schedule_synchronize_now_subscription(self.subscription)

    def mark_unwatched(self):
        from YtManagerApp.management.jobs.synchronize import schedule_synchronize_now_subscription
        self.watched = False
        self.save()
        schedule_synchronize_now_subscription(self.subscription)

    def get_files(self):
        if self.downloaded_path is not None:
            directory, file_pattern = os.path.split(self.downloaded_path)
            for file in os.listdir(directory):
                if file.startswith(file_pattern):
                    yield os.path.join(directory, file)

    def delete_files(self):
        if self.downloaded_path is not None:
            from YtManagerApp.management.jobs.delete_video import schedule_delete_video
            from YtManagerApp.appconfig import get_user_config
            from YtManagerApp.management.jobs.synchronize import schedule_synchronize_now_subscription

            schedule_delete_video(self)

            # Mark watched?
            user_cfg = get_user_config(self.subscription.user)
            if user_cfg.getboolean('user', 'MarkDeletedAsWatched'):
                self.watched = True
                schedule_synchronize_now_subscription(self.subscription)

    def download(self):
        if not self.downloaded_path:
            from YtManagerApp.management.jobs.download_video import schedule_download_video
            schedule_download_video(self)

    def __str__(self):
        return self.name
