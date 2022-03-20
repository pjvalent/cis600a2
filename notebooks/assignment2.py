from audioop import avg
import twitter
import cookbook as cb
import networkx as nx
import matplotlib.pyplot as plt

def make_twitter():
  CONSUMER_KEY = 'fjRSNYpRexhGGEBRZ6wDtR46W' #API key
  CONSUMER_SECRET = 'TsN5f7qN6SHUFliBptqqu4FFh3YLx6tisldkvFx5C065HiwaoE'#secret api key
  OAUTH_TOKEN = '804135069988306947-WoNcUYrqIJsfcdKegraukBv3oF4hsKA' #OAUTH1 token
  OAUTH_TOKEN_SECRET = 'x3O77abe4vDaQ40ad8h5SforRGoLY7G9kBjOiRuTBrnEj' #OAUTH1 secret token

  username = "edmundyu1001"

  """
  Connection to twitter API, used in cell 1 of the twitter cookbook, added my credentials and username here
  """
  auth = twitter.oauth.OAuth(OAUTH_TOKEN, OAUTH_TOKEN_SECRET, CONSUMER_KEY, CONSUMER_SECRET)

  twitter_api = twitter.Twitter(auth=auth)
  return twitter_api

def crawl(twitter_api, username):
  """
  This function finds the five most popular reciprocal friends of the user.
  Takes list of friend IDS and follower IDS
  Uses set notation from slides to get the reciprocal friends, then convert to a list
  Ranks the reciprocal friends based on number of followers and returns list of 5 reciprocal friends with the most followers.
  All functions called using cb.foobar are from the cookbook which is imported as cb
  """

  def find_five_pop_reciprocals(friends_ids, followers_ids):
      reciprocal_friends = set(friends_ids) & set(followers_ids)
      l_recip = list(reciprocal_friends)

      first_100 = l_recip[:100]

      followers_with_count = []

      i = 0
      five_most_popular = []
      while i < len(l_recip):
          friend_batch = l_recip[i:i+100]
          print("friend_batch: ", len(friend_batch))
          response = cb.get_user_profile(twitter_api, user_ids=friend_batch)
          for r in response:
              followers_with_count.append((response[r]["id"],response[r]["followers_count"]))
          i += 100
      #sort by usercount and do so in decending order
      followers_with_count.sort(key=lambda x: x[1],reverse=True)

      #grab only the five first followers
      top_five = followers_with_count[:5]
      print("top five: ", top_five)
      #turn into a list for usability
      fmp_user_ids = [i[0] for i in top_five]

      return fmp_user_ids

  #Creating graph using networkx, this will be the social media graph of the reciprocal friends
  G = nx.Graph()
  ids = [165035772]

  key = 165035772

  G.add_nodes_from(ids)

  """
  Grabbing the followers and friends of the initial user
  """
  jfk = cb.make_twitter_request(twitter_api.followers.ids, screen_name=username, count = 5000)
  iop = cb.make_twitter_request(twitter_api.friends.ids, screen_name=username, count=5000)

  followers = jfk["ids"]
  friends = iop["ids"]

  # find the 5 most popular reciprocals of the user
  top_five_recip = find_five_pop_reciprocals(friends, followers)

  # print("top five recip: ", top_five_recip)


  # ad the top five reciprocals to the ids list, going to do DFS on those until we have 100 ids
  ids += top_five_recip

  next_queue = top_five_recip

  #adding the top 5 reciprocal friends as nodes to the graph
  G.add_nodes_from(top_five_recip)
  #make edges between the nodes
  edges = map(lambda e: (key, e), top_five_recip)
  G.add_edges_from(edges)




  depth = 1
  max_depth = 5
  """
  This crawler is largley derived from the slides, with modifications to fit the parameters of the assignment.
  Crawls until the max depth has been reached, i.e the distance 5 reciprocal friends, or until the graph contains 100 nodes
  """
  while depth < max_depth and len(ids) < 100:
    depth += 1
    (queue, next_queue) = (next_queue,[])

    for id in queue:
      response_a = cb.make_twitter_request(twitter_api.followers.ids, user_id=id, count = 5000) 
      response_b = cb.make_twitter_request(twitter_api.friends.ids, user_id=id, count=5000)
      if response_a is not None and response_b is not None:
        followers = response_a["ids"]
        friends = response_b["ids"]
    
        #getting the top 5 reciprocal friends
        top_five_recip = find_five_pop_reciprocals(friends, followers)
 

        # building the social network as the crawler works
        G.add_nodes_from(top_five_recip)

        #at every iteration, the nodes will be added as will the edges
        edges = map(lambda e: (id, e), top_five_recip)
        G.add_edges_from(edges)

        #checking to make sure top_five_recip is not empty / None type
        if top_five_recip:
          print("Got followers for {0}: {1}".format(id,top_five_recip))
          for i in top_five_recip:
            if(i not in next_queue and i not in ids): 
              next_queue.append(i)
        else:
          print(str(id) + "is protected")

      ids += next_queue

  #sanity check
  print(ids)

  #calculating the diameter of the graph after the crawler has finished
  diameter = nx.diameter(G)
  print("Diameter of graph: ", diameter)
  #calculate average length of shortest path between nodes in the graph
  avg_length = nx.average_shortest_path_length(G)
  print("Average length: ", avg_length)

  #Drawing the graph using networkx
  nx.draw(G)
  plt.savefig("mygraph.png", dpi=1000)
  plt.show()

if __name__ == "__main__":

  username = "edmundyu1001"

  twitter_api = make_twitter()
  crawl(twitter_api, username)