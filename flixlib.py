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

class Movie:
    def __init__(self, netflix, gtitle):
        self.gtitle = gtitle
        time.sleep(0.1)
        matches = netflix.search_titles(gtitle, max_results=1)
        time.sleep(0.1)
        details = netflix.get_title(matches['catalog'][0]['id'])
        for k,v in details['catalog_title'].items():
            setattr(self, k, v)
        self.predictions = {}

def pick_a_movie(location, netflix, users):
    page = urlopen('%s?near=%s' % (GOOGLE_URL, location))
    soup = BeautifulSoup(page)
    movies = []
    print 'finding movies'
    for divmovie in soup.findAll('div', attrs={'class': 'movie'}):
        title = divmovie.find('div', attrs={'class': 'name'}).text
        if title in [movie.gtitle for movie in movies]: continue
        movies.append(Movie(netflix, title))
        # sys.stdout.write('.')
    for user in users:
        print 'parsing %s' % user.nickname
        all_ids = [movie.id for movie in movies]
        ratings = []
        for i in range(0, len(all_ids), MAX_RESULTS):
            time.sleep(0.1)
            partratings = user.get_rating(all_ids[i:i+MAX_RESULTS])['ratings']
            ratings.extend(partratings)
        for rating in ratings:
            for movie in movies:
                if movie.id == rating['href']:
                    movie.predictions[user.nickname] = rating['predicted_rating']
    return movies

def create_connections(config):
    netflix = NetflixAPIV2(config['app_name'],
                           config['api_key'],
                           config['api_secret'])
    users = []
    for val in config['users'].itervalues():
        time.sleep(0.1)
        user = netflix.get_user(val['access_token'],
                                val['access_token_secret'])
        for k, v in user.get_details()['user'].items():
            setattr(user, k, v)
        users.append(user)
    return netflix, users

def print_favorites(movies, user):
    best_rated = sorted(movies,
                        key=lambda x: x.predictions[user.nickname],
                        reverse=True)
    print user.nickname
    for movie in best_rated:
        if movie.average_rating != movie.predictions[user.nickname]:
            print 'Pr %s\tGT %s\tNT %s' % (
                movie.predictions[user.nickname],
                movie.gtitle[:20],
                movie.title['title_short'][:20]
            )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("zipcode")
    args = parser.parse_args()

    with open('config.json', 'r') as f:
        config = json.loads(f.read())

    # account = config['users']['billwanjohi']
    # user = netflix.get_user(account['access_token'],
    #                         account['access_token_secret'])
    # results = netflix.search_titles("'%s'" % args.movie_title)
    # ratings = user.get_rating([results['catalog'][0]['id']])
    # for rating in ratings['ratings']:
    #     print "%s : %s" % (rating['title'], rating['predicted_rating'])

    netflix, users = create_connections(config)
    movies = pick_a_movie(args.zipcode, netflix, users)
    # for k, v in movies.items():
    #     if 'billwanjohi' in v:
    #         print 'B %s A %s Name %s' % (round(v['billwanjohi'],1),
    #                                      round(v['average'],1), k)
    [print_favorites(movies, user) for user in users]

if __name__ == "__main__":
    sys.exit(main())
