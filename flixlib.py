#!/usr/bin/env python
'''Little script to grab rental history'''

import argparse
import re
from urllib2 import urlopen
import sys
import time

from BeautifulSoup import BeautifulSoup
import simplejson as json
from pyflix2 import *

MAX_RESULTS = 500
GOOGLE_URL = "http://www.google.com/movies"
EXPANDS.append('@average_rating')

def get_full_history(user):
    print 'grabbing first 500'
    time.sleep(0.1)
    first500 = user.get_rental_history(max_results=500)
    full_history = first500['rental_history']
    histlength = first500['no_of_results']
    histindex = MAX_RESULTS
    while histindex < histlength:
        time.sleep(0.1)
        print 'grabbing %s to %s' % (
            histindex, min(histindex + MAX_RESULTS - 1, histlength)
        )
        time.sleep(0.1)
        full_history.extend(
            user.get_rental_history(max_results=MAX_RESULTS,
                                    start_index=histindex)
        )   
        histindex += MAX_RESULTS
    return full_history

def write_histories_to_file(netflix, accounts):
    for account in accounts.itervalues():
        time.sleep(0.1)
        user = netflix.get_user(account['access_token'],
                                account['access_token_secret'])
        time.sleep(0.1)
        usr_deets = user.get_details()
        name = usr_deets['user']['last_name']
        print name
        full_history = get_full_history(user)
        print 'writing to file'
        with open('user_%s_hist.json' % name, 'w') as f:
            f.write(json.dumps(full_history))

'''
1. pull movie titles from google as set
2. pop titles and make objects with stuff

movielist = { 
              'tree of life' : {
                'predicted_rating' : 4.5,
                'netflix_id' : 'api.netflix.blah'
              },
              'field of dreams' : True
            }
'''

def find_a_movie(location, netflix, accounts):
    page = urlopen('%s?near=%s' % (GOOGLE_URL, location))
    soup = BeautifulSoup(page)
    counter = 0
    movies = {} # this should be a list
    for movie in soup.findAll('div', attrs={'class': 'movie'}):
        title = movie.find('div', attrs={'class': 'name'}).text
        if title in movies: continue
        movies[title] = {'distance_rank' : counter}
        counter += 1
    for movie in movies:
        time.sleep(0.1)
        results = netflix.search_titles(movie, max_results=1)
        title = netflix.get_title(results['catalog'][0]['id'])
        movies[movie]['netflix_id'] = title['catalog_title']['id']
        movies[movie]['average'] = title['catalog_title']['average_rating']
    for username, creds in accounts.items():
        print 'parsing %s' % username
        time.sleep(0.1)
        user = netflix.get_user(creds['access_token'],
                                creds['access_token_secret'])
        all_ids = [movie['netflix_id'] for movie in movies.itervalues()]
        ratings = []
        for i in range(0, len(all_ids), MAX_RESULTS):
            time.sleep(0.1)
            partratings = user.get_rating(
                    all_ids[i:i+MAX_RESULTS]
                )['ratings']
            ratings.extend(partratings)
        for rating in ratings:
            for mkey, mvalue in movies.items():
                if mvalue['netflix_id'] == rating['href']:
                    movies[mkey][username] = rating['predicted_rating']
    return movies

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("zipcode")
    args = parser.parse_args()

    with open('config.json', 'r') as f:
        config = json.loads(f.read())
    time.sleep(0.1)
    netflix = NetflixAPIV2(config['app_name'],
                           config['api_key'],
                           config['api_secret'])

    # write_histories_to_file(netflix, config['users'])

    # account = config['users']['billwanjohi']
    # user = netflix.get_user(account['access_token'],
    #                         account['access_token_secret'])
    # results = netflix.search_titles("'%s'" % args.movie_title)
    # ratings = user.get_rating([results['catalog'][0]['id']])
    # for rating in ratings['ratings']:
    #     print "%s : %s" % (rating['title'], rating['predicted_rating'])

    movies = find_a_movie(args.zipcode, netflix, config['users'])
    # for k, v in movies.items():
    #     if 'billwanjohi' in v:
    #         print 'B %s A %s Name %s' % (round(v['billwanjohi'],1),
    #                                      round(v['average'],1), k)
    top_picks = sorted(movies.iteritems(), key=['billwanjohi']['predicted_rating'])
    for i in range(3):
        print top_picks[i]

if __name__ == "__main__":
    sys.exit(main())
