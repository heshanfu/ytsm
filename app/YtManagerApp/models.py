import logging
from typing import Callable, Union, Any, Optional
import os

from django.contrib.auth.models import User
from django.contrib.auth.models import User
from django.db import models
from django.db.models.functions import Lower
from YtManagerApp.utils import youtube

# help_text = user shown text
# verbose_name = user shown name
# null = nullable, blank = user is allowed to set value to empty
VIDEO_ORDER_CHOICES = [
    ('newest', 'Newest'),
    ('oldest', 'Oldest'),
    ('playlist', 'Playlist order'),
    ('playlist_reverse', 'Reverse playlist order'),
    ('popularity', 'Popularity'),
    ('rating', 'Top rated'),
]

VIDEO_ORDER_MAPPING = {
    'newest': '-publish_date',
    'oldest': 'publish_date',
    'playlist': 'playlist_index',
    'playlist_reverse': '-playlist_index',
    'popularity': '-views',
    'rating': '-rating'
}


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
        choices=VIDEO_ORDER_CHOICES,
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

    def __repr__(self):
        return f'folder {self.id}, name="{self.name}"'

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


class Subscription(models.Model):
    name = models.CharField(null=False, max_length=1024)
    parent_folder = models.ForeignKey(SubscriptionFolder, on_delete=models.CASCADE, null=True, blank=True)
    playlist_id = models.CharField(null=False, max_length=128)
    description = models.TextField()
    channel_id = models.CharField(max_length=128)
    channel_name = models.CharField(max_length=1024)
    icon_default = models.CharField(max_length=1024)
    icon_best = models.CharField(max_length=1024)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # overrides
    auto_download = models.BooleanField(null=True, blank=True)
    download_limit = models.IntegerField(null=True, blank=True)
    download_order = models.CharField(
        null=True, blank=True,
        max_length=128,
        choices=VIDEO_ORDER_CHOICES)
    delete_after_watched = models.BooleanField(null=True, blank=True)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'subscription {self.id}, name="{self.name}", playlist_id="{self.playlist_id}"'

    def fill_from_playlist(self, info_playlist: youtube.Playlist):
        self.name = info_playlist.title
        self.playlist_id = info_playlist.id
        self.description = info_playlist.description
        self.channel_id = info_playlist.channel_id
        self.channel_name = info_playlist.channel_title
        self.icon_default = youtube.default_thumbnail(info_playlist).url
        self.icon_best = youtube.best_thumbnail(info_playlist).url

    def copy_from_channel(self, info_channel: youtube.Channel):
        # No point in storing info about the 'uploads from X' playlist
        self.name = info_channel.title
        self.playlist_id = info_channel.uploads_playlist.id
        self.description = info_channel.description
        self.channel_id = info_channel.id
        self.channel_name = info_channel.title
        self.icon_default = youtube.default_thumbnail(info_channel).url
        self.icon_best = youtube.best_thumbnail(info_channel).url

    def fetch_from_url(self, url, yt_api: youtube.YoutubeAPI):
        url_parsed = yt_api.parse_url(url)
        if 'playlist' in url_parsed:
            info_playlist = yt_api.playlist(url=url)
            if info_playlist is None:
                raise ValueError('Invalid playlist ID!')

            self.fill_from_playlist(info_playlist)
        else:
            info_channel = yt_api.channel(url=url)
            if info_channel is None:
                raise ValueError('Cannot find channel!')

            self.copy_from_channel(info_channel)

    def delete_subscription(self, keep_downloaded_videos: bool):
        self.delete()

    def get_overloads_dict(self) -> dict:
        d = {}
        if self.auto_download is not None:
            d['AutoDownload'] = self.auto_download
        if self.download_limit is not None:
            d['DownloadSubscriptionLimit'] = self.download_limit
        if self.download_order is not None:
            d['DownloadOrder'] = self.download_order
        if self.delete_after_watched is not None:
            d['DeleteWatched'] = self.delete_after_watched
        return d


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

    @staticmethod
    def create(playlist_item: youtube.PlaylistItem, subscription: Subscription):
        video = Video()
        video.video_id = playlist_item.resource_video_id
        video.name = playlist_item.title
        video.description = playlist_item.description
        video.watched = False
        video.downloaded_path = None
        video.subscription = subscription
        video.playlist_index = playlist_item.position
        video.publish_date = playlist_item.published_at
        video.icon_default = youtube.default_thumbnail(playlist_item).url
        video.icon_best = youtube.best_thumbnail(playlist_item).url
        video.save()
        return video

    def mark_watched(self):
        self.watched = True
        self.save()
        if self.downloaded_path is not None:
            from YtManagerApp.appconfig import settings
            from YtManagerApp.management.jobs.delete_video import schedule_delete_video
            from YtManagerApp.management.jobs.synchronize import schedule_synchronize_now_subscription

            if settings.getboolean_sub(self.subscription, 'user', 'DeleteWatched'):
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
            from YtManagerApp.appconfig import settings
            from YtManagerApp.management.jobs.synchronize import schedule_synchronize_now_subscription

            schedule_delete_video(self)

            # Mark watched?
            if settings.getboolean_sub(self, 'user', 'MarkDeletedAsWatched'):
                self.watched = True
                schedule_synchronize_now_subscription(self.subscription)

    def download(self):
        if not self.downloaded_path:
            from YtManagerApp.management.jobs.download_video import schedule_download_video
            schedule_download_video(self)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'video {self.id}, video_id="{self.video_id}"'
