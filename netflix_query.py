#!/usr/bin/env python

"""netflix_query

Usage:
  netflix_query.py predict -
  netflix_query.py predict [--location=<location>]
  netflix_query.py predict [--movie=<movie>]
  netflix_query.py recommend

"""

import docopt
import re
import sys
import time
import urllib2

from BeautifulSoup import BeautifulSoup
import simplejson as json
from pyflix2 import NetflixAPIV2, EXPANDS

MAX_RESULTS = 500
GOOGLE_URL = "http://www.google.com/movies"
EXPANDS.append('@average_rating')


def main():
    args = docopt.docopt(__doc__)

    with open('config.json', 'r') as f:
        config = json.loads(f.read())
    netflix, users = create_connections(config)

    if args['recommend']:
        recommend(args, users)
    elif args['predict'] and args['-']:
        for line in sys.stdin:
            print Movie(netflix, line)
    elif args['--location']:
        movies = pick_a_movie(args['--location'], netflix, users)
        [print_favorites(movies, user) for user in users]
    elif args['--movie']:
        print Movie(netflix, args['--movie'])


def recommend(args, users):
    """get all recommendations, construct hash, print results"""
    candidates = {}
    for user in users:
        time.sleep(0.1)
        user_recs = user.get_recommendations(
                start_index=0, max_results=5)['recommendations']
        # TODO: get more than one batch, recursively
        #recommendations +=...
        for rec in user_recs:
            candidates[rec['id']] = {
                    'name': rec['title']['title_short'],
                    "{}_prediction".format(user.last_name):
                        rec['predicted_rating']}
        # TODO: also include rated titles
        #actual_ratings =  user.get_actual_rating()
    for candidate in candidates.values():
        candidate['combined_rating'] = sum(filter(None,
                (candidate.get('Taplin_prediction'),
                 candidate.get('Wanjohi_prediction'))))
    print sorted(candidates.values(),
            key=lambda x: x['combined_rating'], reverse=True)


class Movie:
    def __init__(self, netflix, gtitle):
        self.gtitle = gtitle
        time.sleep(0.1)
        matches = netflix.search_titles(gtitle, max_results=1, expand='@title')
        for k, v in matches['catalog'][0].items():
            setattr(self, k, v)
        self.predictions = {}

    def __str__(self):
        return '%s - %s' % (self.title['title_short'], self.average_rating)


def pick_a_movie(location, netflix, users):
    movies = []
    print 'finding movies'
    for block in range(0, 50, 10):
        page = urllib2.urlopen('{0}?near={1}&start={2}&date={3}'.format(
            GOOGLE_URL, location, block, 0))
        soup = BeautifulSoup(page)
        for divmovie in soup.findAll('div', attrs={'class': 'movie'}):
            title = divmovie.find('div', attrs={'class': 'name'}).text
            title = re.sub(r'\b3d\b', '', title, flags=re.IGNORECASE)
            if title in [movie.gtitle for movie in movies]:
                continue
            movies.append(Movie(netflix, title))
    print 'found {0} movies'.format(len(movies))
    for user in users:
        print 'parsing %s' % user.last_name
        all_ids = [movie.id for movie in movies]
        ratings = []
        for i in range(0, len(all_ids), MAX_RESULTS):
            time.sleep(0.1)
            partratings = user.get_rating(all_ids[i:i + MAX_RESULTS])['ratings']
            ratings.extend(partratings)
        for rating in ratings:
            for movie in movies:
                if movie.id == rating['href']:
                    movie.predictions[user.last_name] = rating['predicted_rating']
    return movies


def create_connections(config):
    netflix = NetflixAPIV2(config['app_name'],
                           config['api_key'],
                           config['api_secret'])
    users = []
    for val in config['users'].itervalues():
        time.sleep(0.1)
        user = netflix.get_user(val['user_id'],
                                val['access_token'],
                                val['access_token_secret'])
        for k, v in user.get_details()['user'].items():
            setattr(user, k, v)
        users.append(user)
    return netflix, users


def print_favorites(movies, user):
    best_rated = sorted(movies,
                        key=lambda x: x.predictions[user.last_name],
                        reverse=True)
    print user.last_name
    for movie in best_rated:
        uniq = set(movie.predictions.values())
        uniq.add(movie.average_rating)
        if len(uniq) > 1:
            print 'Pr %s\tGT %s\tNT %s' % (
                movie.predictions[user.last_name],
                movie.gtitle[:20],
                movie.title['title_short'][:20]
            )


if __name__ == "__main__":
    sys.exit(main())
