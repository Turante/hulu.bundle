import random

TITLE = 'Hulu'
ART = 'art-default.jpg'
ICON = 'icon-default.png'

URL_LISTINGS      = 'http://www.hulu.com/browse/search?keyword=&alphabet=All&family_friendly=0&closed_captioned=0&channel=%s&subchannel=&network=All&display=%s&decade=All&type=%s&view_as_thumbnail=true&block_num=%s'
EPISODE_LISTINGS  = 'http://www.hulu.com/videos/slider?classic_sort=asc&items_per_page=%d&season=%s&show_id=%s&show_placeholders=1&sort=original_premiere_date&type=episode'
URL_QUEUE         = 'http://www.hulu.com/profile/queue?view=list&kind=thumbs&order=asc&page=%d&sort=position'

REGEX_CHANNEL_LISTINGS      = Regex('Element.replace\("channel", "(.+)\);')
REGEX_SHOW_LISTINGS         = Regex('Element.(update|replace)\("(show_list|browse-lazy-load)", "(?P<content>.+)\);')
REGEX_RECOMMENDED_LISTINGS  = Regex('Element.update\("rec-hub-main", "(.+)\);')
REGEX_RATING_FEED           = Regex('Rating: ([^ ]+) .+')
REGEX_TV_EPISODE_FEED       = Regex('(?P<show>[^-]+) - s(?P<season>[0-9]+) \| e(?P<episode>[0-9]+) - (?P<title>.+)$')
REGEX_TV_EPISODE_LISTING    = Regex('Season (?P<season>[0-9]+) : Ep. (?P<episode>[0-9]+).*\(((?P<hours>[0-9])+:)?(?P<mins>[0-9]+):(?P<secs>[0-9]+)\)', Regex.DOTALL)
REGEX_TV_EPISODE_EMBED      = Regex('Season (?P<season>[0-9]+)\s+.+')
REGEX_TV_EPISODE_QUEUE      = Regex('S(?P<season>[0-9]+) : Ep\. (?P<episode>[0-9]+)')

NAMESPACES      = {'activity': 'http://activitystrea.ms/spec/1.0/',
                   'media': 'http://search.yahoo.com/mrss/'}

####################################################################################################
def Start():

  Plugin.AddViewGroup('InfoList', viewMode = 'InfoList', mediaType = 'items')
  Plugin.AddViewGroup('List', viewMode = 'List', mediaType = 'items')

  ObjectContainer.title1 = TITLE
  ObjectContainer.art = R(ART)
  ObjectContainer.view_group = 'List'

  DirectoryObject.thumb = R(ICON)
  DirectoryObject.art = R(ART)

  VideoClipObject.thumb = R(ICON)
  VideoClipObject.art = R(ART)

  HTTP.CacheTime = CACHE_1HOUR
  HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:18.0) Gecko/20100101 Firefox/18.0'

  loginResult = HuluLogin()
  Log("Login success: " + str(loginResult))

####################################################################################################
def HuluLogin():

  username = Prefs["email"]
  password = Prefs["password"]

  if (username != None) and (password != None):
    authentication_url = "https://secure.hulu.com/account/authenticate?" + str(int(random.random()*1000000000))
    authentication_headers = {"Cookie": "sli=1; login=" + username + "; password=" + password + ";"}
    resp = HTTP.Request(authentication_url, headers = authentication_headers, cacheTime=0).content

    if resp == "Login.onComplete();":
      HTTP.Headers['Cookie'] = HTTP.CookiesForURL('https://secure.hulu.com/')

      for item in HTTP.CookiesForURL('https://secure.hulu.com/').split(';'):
        if '_hulu_uid' in item :
          Dict['_hulu_uid'] = item[11:]
      return True
    else:
      return False
  else:
    return False

####################################################################################################
@handler('/video/hulu', TITLE, thumb=ICON, art=ART)
def MainMenu():

  oc = ObjectContainer()
  oc.add(DirectoryObject(key = Callback(MyHulu, title = "My Hulu"), title = "My Hulu"))
  oc.add(DirectoryObject(key = Callback(Channels, title = "TV", item_type = "tv", display = "Shows%20with%20full%20episodes%20only"), title = "TV"))
  oc.add(DirectoryObject(key = Callback(Channels, title = "Movies", item_type = "movies", display = "Full%20length%20movies%20only"), title = "Movies"))
  oc.add(DirectoryObject(key = Callback(MostPopular, title = "Popular Videos"), title = "Popular Videos"))
  oc.add(DirectoryObject(key = Callback(MostRecent, title = "Recently Added"), title = "Recently Added"))
  oc.add(DirectoryObject(key = Callback(Feeds, title = "Highest Rated Videos", feed_url = "http://www.hulu.com/feed/highest_rated/videos"), title = "Highest Rated Videos"))
  oc.add(DirectoryObject(key = Callback(Feeds, title = "Soon-to-Expire Videos", feed_url = "http://www.hulu.com/feed/expiring/videos"), title = "Soon-to-Expire Videos"))
  oc.add(SearchDirectoryObject(identifier="com.plexapp.plugins.hulu", title = "Search...", prompt = "Search for Videos", thumb = R('search.png')))
  oc.add(PrefsObject(title = 'Preferences', thumb = R('icon-prefs.png')))
  return oc

####################################################################################################
@route('/video/hulu/myhulu')
def MyHulu(title):

  # Attempt to login
  loginResult = HuluLogin()  
  Log("MyHulu Login success: " + str(loginResult))

  if loginResult:
    oc = ObjectContainer()
    oc.add(DirectoryObject(key = Callback(Queue, title = "My Queue"), title = "My Queue"))
    oc.add(DirectoryObject(key = Callback(Recommended, title = "TV Show Recommendations", url = "http://www.hulu.com/recommendation/search?closed_captioned=0&video_type=TV"), title = "TV Show Recommendations"))
    oc.add(DirectoryObject(key = Callback(Recommended, title = "Movie Recommendations", url = "http://www.hulu.com/recommendation/search?closed_captioned=0&video_type=Movie"), title = "Movie Recommendations"))
    oc.add(DirectoryObject(key = Callback(Favorites, title = "My Favorites"), title = "My Favorites"))
  else:
    oc = ObjectContainer(header="User info required", message="Please enter your Hulu email address and password in Preferences.")
  return oc

####################################################################################################
@route('/video/hulu/channels')
def Channels(title, item_type, display):

  oc = ObjectContainer(title2 = title)
  channels_page = HTTP.Request(URL_LISTINGS % ("All", display, item_type, 0)).content
  html_content = REGEX_CHANNEL_LISTINGS.findall(channels_page)[0].decode('unicode_escape')
  html_page = HTML.ElementFromString(html_content)

  for genre in html_page.xpath('//div[@class="cbx-options"]//li'):
    channel = genre.get('value')
    oc.add(DirectoryObject(
      key = Callback(ListShows, title = channel, channel = channel, item_type = item_type, display = display),
      title = channel))

  return oc

####################################################################################################
@route('/video/hulu/popular')
def MostPopular(title):

  oc = ObjectContainer(title2 = title)
  oc.add(DirectoryObject(key = Callback(Feeds, title = "Popular Videos Today", feed_url = "http://www.hulu.com/feed/popular/videos/today"), title = "Popular Videos Today"))
  oc.add(DirectoryObject(key = Callback(Feeds, title = "Popular Videos This Week", feed_url = "http://www.hulu.com/feed/popular/videos/this_week"), title = "Popular Videos This Week"))
  oc.add(DirectoryObject(key = Callback(Feeds, title = "Popular Videos This Month", feed_url = "http://www.hulu.com/feed/popular/videos/this_month"), title = "Popular Videos This Month"))
  oc.add(DirectoryObject(key = Callback(Feeds, title = "Popular Videos of All Time", feed_url = "http://www.hulu.com/feed/popular/videos/all_time"), title = "Popular Videos of All Time"))
  return oc

####################################################################################################
@route('/video/hulu/recent')
def MostRecent(title):

  oc = ObjectContainer(title2 = title)
  oc.add(DirectoryObject(key = Callback(Feeds, title = "Recently Added Shows", feed_url = "http://www.hulu.com/feed/recent/shows"), title = "Recently Added Shows"))
  oc.add(DirectoryObject(key = Callback(Feeds, title = "Recently Added Movies", feed_url = "http://www.hulu.com/feed/recent/movies"), title = "Recently Added Movies"))
  oc.add(DirectoryObject(key = Callback(Feeds, title = "Recently Added Videos", feed_url = "http://www.hulu.com/feed/recent/videos"), title = "Recently Added Videos"))
  return oc

####################################################################################################
@route('/video/hulu/feeds')
def Feeds(title, feed_url):

  oc = ObjectContainer(title2 = title)
  feed = XML.ElementFromURL(feed_url)

  for item in feed.xpath('//channel/item'):
    url = item.xpath('.//guid/text()')[0]
    thumb = item.xpath('.//media:thumbnail', namespaces = NAMESPACES)[0].get('url').split('?')[0] + '?size=512x288'
    date = Datetime.ParseDate(item.xpath('.//pubDate/text()')[0])

    summary_text = item.xpath('.//description/text()')[0]
    summary_node = HTML.ElementFromString(summary_text)
    summary = summary_node.xpath('.//p/text()')[0]
 
    rating = None
    try: rating = float(REGEX_RATING_FEED.findall(summary_text)[0]) * 2
    except: pass

    title = item.xpath('.//title/text()')[0].replace("\n", " ")
    try:

      # A feed will normally contain individual episodes. Their titles are of formats similar to the following:
      #    The Voice - s2 | e15 - Quarterfinals: Live Eliminations
      # If we detect this, then we can extract the available information. If this fails, then we will simply 
      # fallback to a normal VideoClipObject
      details = REGEX_TV_EPISODE_FEED.match(title).groupdict()

      oc.add(EpisodeObject(
        url = url,
        title = details['title'],
        summary = summary,
        show = details['show'],
        season = int(details['season']),
        index = int(details['episode']),
        thumb = thumb,
        originally_available_at = date,
        rating = rating
      ))
    except:
      oc.add(VideoClipObject(
        url = url,
        title = title,
        summary = summary,
        thumb = thumb,
        originally_available_at = date,
        rating = rating
      ))

  return oc

####################################################################################################
@route('/video/hulu/shows/{page}', page=int)
def ListShows(title, channel, item_type, display, page = 0):
  
  oc = ObjectContainer()
  result = {}

  @parallelize
  def GetShows(channel=channel, item_type=item_type, display=display, page=page):

    channel = channel.replace(' ','%20')
    shows_page = HTTP.Request(URL_LISTINGS % (channel, display, item_type, str(page))).content
    html_content = REGEX_SHOW_LISTINGS.search(shows_page).group('content').decode('unicode_escape')
    html_page = HTML.ElementFromString(html_content)
    shows = html_page.xpath('//a[@class = "info_hover"]')

    for num in range(len(shows)):
      show = shows[num]

      @task
      def GetShow(num=num, result=result, item=show):
        original_url = item.get('href').split('?')[0]

        if original_url.startswith('http://www.hulu.com/') == False:
          pass

        # There are a very, very small percentage of videos for which they appear to contain 'invalid'
        # JSON. At present, there is no known workaround, so we should simply skip it.
        info_url = original_url.replace('http://www.hulu.com/', 'http://www.hulu.com/shows/info/')
        try: details = JSON.ObjectFromURL(info_url, headers = {'X-Requested-With': 'XMLHttpRequest'})
        except: pass

        tags = []
        if 'taggings' in details:
          tags = [ tag['tag_name'] for tag in details['taggings'] ]

        if details.has_key('films_count'):
          result[num] = MovieObject(
            url = original_url,
            title = details['name'],
            summary = details['description'],
            thumb = details['thumbnail_url'],
            tags = tags,
            originally_available_at = Datetime.ParseDate(details['film_date'])
          )

        elif details.has_key('episodes_count') and details['episodes_count'] > 0:
          result[num] = TVShowObject(
            key = Callback(ListSeasons, title = details['name'], show_url = original_url, info_url = info_url, show_id = details['id']),
            rating_key = original_url,
            title = details['name'],
            summary = details['description'],
            thumb = details['thumbnail_url'],
            episode_count = details['episodes_count'],
            viewed_episode_count = 0,
            tags = tags
          )

  keys = result.keys()
  keys.sort()

  for key in keys:
    oc.add(result[key])

  # Add an option for the next page. We will only return the MessageContainer if we have at least grabbed one page. If the above
  # code is faulty and the first page fails, we want to return the empty ObjectContainer. This will allow us to detect the error
  # by the tester and hopefully fix the issue quickly.
  if len(oc) > 0:
    oc.add(NextPageObject(
      key = Callback(ListShows, title = title, channel = channel, item_type = item_type, display = display, page = page + 1),
      title = "Next..."))
  elif page > 0:
    return ObjectContainer(header="No More Results", message="There are no more shows...")

  return oc

####################################################################################################
@route('/video/hulu/seasons')
def ListSeasons(title, show_url, info_url, show_id):

  oc = ObjectContainer(title2 = title)
  details = JSON.ObjectFromURL(info_url, headers = {'X-Requested-With': 'XMLHttpRequest'})

  if int(details['seasons_count']) > 1:
    for i in range(int(details['seasons_count'])):
      season_num = str(i+1)

      oc.add(SeasonObject(
        key = Callback(ListEpisodes, title = details['name'], show_id = details['id'], show_name = details['name'], season = int(season_num), show_url = show_url),
        rating_key = show_url,
        show = details['name'],
        index = int(season_num),
        title = "Season %s" % season_num,
        summary = details['description'],
        thumb = details['thumbnail_url'].split('?')[0] + '?size=512x288'
      ))

  else:
    try:
      show_id = details['id']
      show_name = details['name']
      season = ''

      return ListEpisodes(title, show_id, show_name, season, show_url = show_url)
    except: 
      pass

  return oc

####################################################################################################
@route('/video/hulu/episodes')
def ListEpisodes(title, show_id, show_name, season, show_url = None, items_per_page = 5):

  oc = ObjectContainer(title2 = title)
  page = 1
  original_url = EPISODE_LISTINGS % (items_per_page, season, show_id)

  while(True):
    episode_url = original_url + ('&page=%d' % page)
    episodes_page_content = HTTP.Request(episode_url).content

    if len(episodes_page_content) == 0 and page == 1:
      episode_url = original_url + "&category=Full%20Episodes"
      episodes_page_content = HTTP.Request(episode_url).content
      if len(episodes_page_content) == 0 and page == 1:
        episode_url = original_url + "&category=Subtitled"
        episodes_page_content = HTTP.Request(episode_url).content
        if len(episodes_page_content) == 0:
          break
        else:
          original_url = episode_url
      else:
        original_url = episode_url

    episodes_page = HTML.ElementFromString(episodes_page_content)

    # If we have requested a page with no items in it, then there are no more episodes are available
    episodes = episodes_page.xpath('//li')
    if len(episodes) == 0:
      break

    for item in episodes:
      url = item.xpath('.//a')[0].get('href')
      title = item.xpath('.//a/text()')[0]
      thumb = item.xpath('.//img')[0].get('src').split('?')[0] + '?size=512x288'

      details = item.xpath('.//span[@class = "video-info"]/text()')[0]
      details_dict = REGEX_TV_EPISODE_LISTING.match(details).groupdict()
      episode_index = int(details_dict['episode'])

      hours = 0
      try: hours = int(details_dict['hours'])
      except: pass
      mins = int(details_dict['mins'])
      secs = int(details_dict['secs'])
      duration = ((((hours * 60) + mins) * 60) + secs) * 1000

      oc.add(EpisodeObject(
        url = url,
        title = title,
        show = show_name,
        index = episode_index,
        thumb = thumb,
        duration = duration
      ))

    # If we have requested (items_per_page) but less have been provided, then no more episodes are available
    if len(episodes) != items_per_page:
      break

    # Increase the page
    page = page + 1

  if len(oc) == 0 and show_url != None:
    show_page = HTML.ElementFromURL(show_url)

    for item in show_page.xpath('//div[@id = "episode-container"]//div[contains(@class, "vsl-short")]//li'):
      url = item.xpath('.//a')[0].get('href')
      title = item.xpath('./a/text()')[0]
      thumb = item.xpath('.//img[@class = "thumbnail"]')[0].get('src').split('?')[0] + '?size=512x288'

      details = item.xpath('.//span[@class = "video-info"]/text()')[0]
      details_dict = REGEX_TV_EPISODE_LISTING.match(details).groupdict()
      episode_index = int(details_dict['episode'])

      hours = 0
      try: hours = int(details_dict['hours'])
      except: pass
      mins = int(details_dict['mins'])
      secs = int(details_dict['secs'])
      duration = ((((hours * 60) + mins) * 60) + secs) * 1000

      oc.add(EpisodeObject(
        url = url,
        title = title,
        show = show_name,
        index = episode_index,
        thumb = thumb,
        duration = duration
      ))

  # Sort the episodes based upon index
  oc.objects.sort(key = lambda obj: obj.index)

  return oc

####################################################################################################
@route('/video/hulu/queue')
def Queue(title, page = 1):

  oc = ObjectContainer(title2 = title)
  queue_page = HTML.ElementFromURL(URL_QUEUE % page)

  for item in queue_page.xpath('//div[@id = "queue"]//tr[contains(@id, "queue")]'):
    url = item.xpath('.//td[@class = "c2"]//a')[0].get('href')
    title = ''.join(item.xpath('.//td[@class = "c2"]//a//text()'))
    thumb = item.xpath('.//td[@class = "c2"]//img')[0].get('src').split('?')[0] + '?size=512x288'
    date = item.xpath('.//td[@class = "c5"]/text()')[0]
    date = Datetime.ParseDate(date)
    duration = int(TimeToMs(item.xpath('.//td[@class = "c2"]//span/text()')[0]))

    rating_full = len(item.xpath('.//td[@class = "c4"]/img[contains(@src, "full")]'))
    rating_half = len(item.xpath('.//td[@class = "c4"]/img[contains(@src, "half")]'))
    rating = float((2 * rating_full) + rating_half)

    summary = None
    try: summary = item.xpath('.//td[@class = "c2"]//div[@class = "expire-warning"]//text()')[0]
    except: pass

    video_details = item.xpath('.//td[@class = "c3"]/text()')[0]
    if video_details.find('Movie') > -1:
      oc.add(MovieObject(
        url = url,
        title = title,
        summary = summary,
        thumb = thumb,
        rating = rating,
        originally_available_at = date,
        duration = duration
      ))

    else:
      tv_details = REGEX_TV_EPISODE_QUEUE.match(video_details)

      if tv_details != None:
        tv_details_dict = tv_details.groupdict()
        show = title.split(':')[0]
        episode_title = title.split(':')[1]

        oc.add(EpisodeObject(
          url = url,
          show = show,
          title = episode_title,
          summary = summary,
          season = int(tv_details_dict['season']),
          index = int(tv_details_dict['episode']),
          thumb = thumb,
          rating = rating,
          originally_available_at = date,
          duration = duration
        ))

      else:
        oc.add(VideoClipObject(
          url = url,
          title = title,
          summary = summary,
          thumb = thumb,
          rating = rating,
          originally_available_at = date,
          duration = duration
        ))

  # Check to see if the user has any more pages...
  page_control = queue_page.xpath('//div[@class = "page"]')
  if len(page_control) > 0:
    total_pages = int(page_control[0].xpath('.//li[@class = "total"]/a/text()')[0])
    if page < total_pages:
      oc.add(NextPageObject(key = Callback(Queue, title = "My Queue", page = page + 1), title = "Next..."))

  return oc

####################################################################################################
def TimeToMs(timecode):

  seconds = 0
  timecode = timecode.strip('(').rstrip(')')

  try:
    duration = timecode.split(':')
    duration.reverse()

    for i in range(0, len(duration)):
      seconds += int(duration[i]) * (60**i)
  except:
    pass

  return seconds * 1000

####################################################################################################
def Recommended(title, url):

  oc = ObjectContainer()
  shows_page = HTTP.Request(url, headers = {'X-Requested-With': 'XMLHttpRequest'}).content
  html_content = REGEX_RECOMMENDED_LISTINGS.findall(shows_page)[0].decode('unicode_escape')
  html_page = HTML.ElementFromString(html_content)

  for item in html_page.xpath('//span/a[contains(@class, "info_hover")]'):
    original_url = item.get('href').split('?')[0]
    if original_url.startswith('http://www.hulu.com/') == False:
      continue

    info_url = original_url.replace('http://www.hulu.com/', 'http://www.hulu.com/shows/info/')
    details = JSON.ObjectFromURL(info_url, headers = {'X-Requested-With': 'XMLHttpRequest'})

    tags = []
    if 'taggings' in details:
      tags = [ tag['tag_name'] for tag in details['taggings'] ]

    if details.has_key('films_count'):
      oc.add(MovieObject(
        url = original_url,
        title = details['name'],
        summary = details['description'],
        thumb = details['thumbnail_url'].split('?')[0] + '?size=512x288',
        tags = tags,
        originally_available_at = Datetime.ParseDate(details['film_date'])
      ))

    elif details.has_key('episodes_count') and details['episodes_count'] > 0:
      oc.add(TVShowObject(
        key = Callback(ListSeasons, title = details['name'], show_url = original_url, info_url = info_url, show_id = details['id']),
        rating_key = original_url,
        title = details['name'],
        summary = details['description'],
        thumb = details['thumbnail_url'].split('?')[0] + '?size=512x288',
        episode_count = details['episodes_count'],
        viewed_episode_count = 0,
        tags = tags
      ))

  return oc

####################################################################################################
@route('/video/hulu/favorites')
def Favorites(title):

  oc = ObjectContainer(title2 = title)
  url = 'http://www.hulu.com/favorites/favorites_nav?user_id=' + Dict['_hulu_uid']
  favourites_page = HTML.ElementFromURL(url)

  for show in favourites_page.xpath("//div[@class='fav-nav-show']"):
    original_url = show.xpath("./a")[0].get("href")
    info_url = original_url.replace('http://www.hulu.com/', 'http://www.hulu.com/shows/info/')
    details = JSON.ObjectFromURL(info_url, headers = {'X-Requested-With': 'XMLHttpRequest'})

    tags = []
    if 'taggings' in details:
      tags = [ tag['tag_name'] for tag in details['taggings'] ]

    oc.add(TVShowObject(
      key = Callback(ListSeasons, title = details['name'], show_url = original_url, info_url = info_url, show_id = details['id']),
      rating_key = original_url,
      title = details['name'],
      summary = details['description'],
      thumb = details['thumbnail_url'].split('?')[0] + '?size=512x288',
      episode_count = details['episodes_count'],
      viewed_episode_count = 0,
      tags = tags
    ))

  return oc
