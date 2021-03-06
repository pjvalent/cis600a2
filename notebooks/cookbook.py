


# ## Example 16. Making robust Twitter requests

# In[22]:


import sys
import time
from urllib.error import URLError
from http.client import BadStatusLine
import json
import twitter

def make_twitter_request(twitter_api_func, max_errors=10, *args, **kw): 
    
    # A nested helper function that handles common HTTPErrors. Return an updated
    # value for wait_period if the problem is a 500 level error. Block until the
    # rate limit is reset if it's a rate limiting issue (429 error). Returns None
    # for 401 and 404 errors, which requires special handling by the caller.
    def handle_twitter_http_error(e, wait_period=2, sleep_when_rate_limited=True):
    
        if wait_period > 3600: # Seconds
            print('Too many retries. Quitting.', file=sys.stderr)
            raise e
    
        # See https://developer.twitter.com/en/docs/basics/response-codes
        # for common codes
    
        if e.e.code == 401:
            print('Encountered 401 Error (Not Authorized)', file=sys.stderr)
            return None
        elif e.e.code == 404:
            print('Encountered 404 Error (Not Found)', file=sys.stderr)
            return None
        elif e.e.code == 429: 
            print('Encountered 429 Error (Rate Limit Exceeded)', file=sys.stderr)
            if sleep_when_rate_limited:
                print("Retrying in 15 minutes...ZzZ...", file=sys.stderr)
                sys.stderr.flush()
                time.sleep(60*15 + 5)
                print('...ZzZ...Awake now and trying again.', file=sys.stderr)
                return 2
            else:
                raise e # Caller must handle the rate limiting issue
        elif e.e.code in (500, 502, 503, 504):
            print('Encountered {0} Error. Retrying in {1} seconds'                  .format(e.e.code, wait_period), file=sys.stderr)
            time.sleep(wait_period)
            wait_period *= 1.5
            return wait_period
        else:
            raise e

    # End of nested helper function
    
    wait_period = 2 
    error_count = 0 

    while True:
        try:
            return twitter_api_func(*args, **kw)
        except twitter.api.TwitterHTTPError as e:
            error_count = 0 
            wait_period = handle_twitter_http_error(e, wait_period)
            if wait_period is None:
                return
        except URLError as e:
            error_count += 1
            time.sleep(wait_period)
            wait_period *= 1.5
            print("URLError encountered. Continuing.", file=sys.stderr)
            if error_count > max_errors:
                print("Too many consecutive errors...bailing out.", file=sys.stderr)
                raise
        except BadStatusLine as e:
            error_count += 1
            time.sleep(wait_period)
            wait_period *= 1.5
            print("BadStatusLine encountered. Continuing.", file=sys.stderr)
            if error_count > max_errors:
                print("Too many consecutive errors...bailing out.", file=sys.stderr)
                raise

# Sample usage

# twitter_api = oauth_login()

# See http://bit.ly/2Gcjfzr for twitter_api.users.lookup

# response = make_twitter_request(twitter_api.users.lookup, 
#                                 screen_name="SocialWebMining")

# print(json.dumps(response, indent=1))


# ## Example 17. Resolving user profile information

# In[23]:


def get_user_profile(twitter_api, screen_names=None, user_ids=None):
   
    # Must have either screen_name or user_id (logical xor)
    assert (screen_names != None) != (user_ids != None),     "Must have screen_names or user_ids, but not both"
    
    items_to_info = {}

    items = screen_names or user_ids
    
    while len(items) > 0:

        # Process 100 items at a time per the API specifications for /users/lookup.
        # See http://bit.ly/2Gcjfzr for details.
        
        items_str = ','.join([str(item) for item in items[:100]])
        items = items[100:]

        if screen_names:
            response = make_twitter_request(twitter_api.users.lookup, 
                                            screen_name=items_str)
        else: # user_ids
            response = make_twitter_request(twitter_api.users.lookup, 
                                            user_id=items_str)
    
        for user_info in response:
            if screen_names:
                items_to_info[user_info['screen_name']] = user_info
            else: # user_ids
                items_to_info[user_info['id']] = user_info

    return items_to_info

# Sample usage

# twitter_api = oauth_login()

# print(get_user_profile(twitter_api, screen_names=["SocialWebMining", "ptwobrussell"]))
#print(get_user_profile(twitter_api, user_ids=[132373965]))


# ## Example 18. Extracting tweet entities from arbitrary text

# In[24]:


# pip install twitter_text
import twitter_text

# Sample usage

# txt = "RT @SocialWebMining Mining 1M+ Tweets About #Syria http://wp.me/p3QiJd-1I"

# ex = twitter_text.Extractor(txt)

# print("Screen Names:", ex.extract_mentioned_screen_names_with_indices())
# print("URLs:", ex.extract_urls_with_indices())
# print("Hashtags:", ex.extract_hashtags_with_indices())


# ## Example 19. Getting all friends or followers for a user

# In[25]:


from functools import partial
from sys import maxsize as maxint

def get_friends_followers_ids(twitter_api, screen_name=None, user_id=None,
                              friends_limit=maxint, followers_limit=maxint):
    
    # Must have either screen_name or user_id (logical xor)
    assert (screen_name != None) != (user_id != None),     "Must have screen_name or user_id, but not both"
    
    # See http://bit.ly/2GcjKJP and http://bit.ly/2rFz90N for details
    # on API parameters
    
    get_friends_ids = partial(make_twitter_request, twitter_api.friends.ids, 
                              count=5000)
    get_followers_ids = partial(make_twitter_request, twitter_api.followers.ids, 
                                count=5000)

    friends_ids, followers_ids = [], []
    
    for twitter_api_func, limit, ids, label in [
                    [get_friends_ids, friends_limit, friends_ids, "friends"], 
                    [get_followers_ids, followers_limit, followers_ids, "followers"]
                ]:
        
        if limit == 0: continue
        
        cursor = -1
        while cursor != 0:
        
            # Use make_twitter_request via the partially bound callable...
            if screen_name: 
                response = twitter_api_func(screen_name=screen_name, cursor=cursor)
            else: # user_id
                response = twitter_api_func(user_id=user_id, cursor=cursor)

            if response is not None:
                ids += response['ids']
                cursor = response['next_cursor']
        
            print('Fetched {0} total {1} ids for {2}'.format(len(ids),                  label, (user_id or screen_name)),file=sys.stderr)
        
            # XXX: You may want to store data during each iteration to provide an 
            # an additional layer of protection from exceptional circumstances
        
            if len(ids) >= limit or response is None:
                break

    # Do something useful with the IDs, like store them to disk...
    return friends_ids[:friends_limit], followers_ids[:followers_limit]

# Sample usage

# twitter_api = oauth_login()

# friends_ids, followers_ids = get_friends_followers_ids(twitter_api, 
#                                                        screen_name="SocialWebMining", 
#                                                        friends_limit=10, 
#                                                        followers_limit=10)

# print(friends_ids)
# print(followers_ids)

def crawl_followers(twitter_api, screen_name, limit=10, depth=2):
    
    # Resolve the ID for screen_name and start working with IDs for consistency 
    # in storage

    #start with the first user
    seed_id = str(twitter_api.users.show(screen_name=screen_name)['id'])
    print("seed id: ", seed_id)
    
    #get the first users friends and followers
    friend_queue, follower_queue = get_friends_followers_ids(twitter_api, user_id=seed_id, 
                                              friends_limit=0, followers_limit=limit)
    """
    TODO: find the reciprocal friends, as done in a2 file cell 2
    TODO: find the 5 most popular reciprocal friends, as done in a2 file
    TODO: create networkx graph, and make the connections between reciprocal friends, and the user
    TODO: calculate diameter of networkx graph
    TODO: calculate average distance of networkx graph
    """
    
    d = 1
    print("entering loop...................")
    while d < depth:
        d += 1
        (queue, follower_queue) = (follower_queue, [])
        for fid in queue:
            friend_ids, follower_ids = get_friends_followers_ids(twitter_api, user_id=fid, 
                                                     friends_limit=0, 
                                                     followers_limit=limit)

            print("adding to follower queue........................")
            follower_queue += follower_ids
            print("len follower queue: ", len(follower_queue))
            friend_queue += friend_ids

