#!/usr/bin/env python

import argparse
import re
import urllib2
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

def write_histories_to_file(netflix, users):
    for user in users:
        time.sleep(0.1)
        print user.nickname
        full_history = get_full_history(user)
        print 'writing to file'
        with open('%s history.json' % user.nickname, 'w') as f:
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
    def __str__(self):
        return '%s - %s' % (self.title['title_short'], self.average_rating)

def pick_a_movie(location, netflix, users):
    page = urllib2.urlopen('%s?near=%s' % (GOOGLE_URL, location))
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
    parser.add_argument('-l', '--location')
    parser.add_argument('-m', '--movie')
    parser.add_argument('-s', '--save', action='store_true')
    args = parser.parse_args()

    with open('config.json', 'r') as f:
        config = json.loads(f.read())
    netflix, users = create_connections(config)

    if args.location:
        movies = pick_a_movie(args.location, netflix, users)
        [print_favorites(movies, user) for user in users]
    elif args.movie:
        movie = Movie(netflix, args.movie)
        print movie
    elif args.save:
        write_histories_to_file(netflix, users)
    else:
        print "don't know what to do"

if __name__ == "__main__":
    sys.exit(main())
