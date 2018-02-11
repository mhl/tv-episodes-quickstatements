import argparse
import json
import re

from gpshared import (
    get_episodes_from_wikipedia, get_episodes_from_wikidata, previous_and_next)

parser = argparse.ArgumentParser(
    description='Generate TV episodes QuickStatements')
parser.add_argument('COMMAND', choices=['create', 'follows', 'has-part', 'prod-code'])
parser.add_argument('SERIES_JSON')

args = parser.parse_args()

with open(args.SERIES_JSON) as f:
    series_data = json.load(f)

SERIES = series_data['series']
SEASONS = [(o['url'], o['item_id']) for o in series_data['seasons']]
EPISODE_DESCRIPTION = series_data['episode_description']

with open('quickstatements-{}.txt'.format(args.COMMAND), 'w') as f:

    if args.COMMAND == 'create':

        for URL, SEASON in SEASONS:
            wp = get_episodes_from_wikipedia(URL)
            wd = get_episodes_from_wikidata(SEASON)

            for episode in wp:
                if wd.get(episode.title):
                    continue
                f.write('CREATE\n')
                f.write('LAST\tLen\t"{label}"\n'.format(label=episode.title))
                f.write('LAST\tDen\t"{description}"\n'.format(description=EPISODE_DESCRIPTION))
                f.write('LAST\tP361\t{season}\n'.format(season=SEASON))
                f.write('LAST\tP31\tQ21191270\n')
                f.write('LAST\tP179\t{series}\tP1545\t"{0.number_overall}"\tS4656\t"{wiki_url}"\n'.format(
                    episode, series=SERIES, wiki_url=URL))
                f.write('LAST\tP179\t{season}\tP1545\t"{0.number_in_season}"\tS4656\t"{wiki_url}"\n'.format(
                    episode, season=SEASON, wiki_url=URL))
                if episode.production_code:
                    f.write('LAST\tP2364\t"{prod_code}"\tS4656\t"{wiki_url}"\n'.format(
                        prod_code=episode.production_code,
                        wiki_url=URL,
                    ))
                if episode.title_url:
                    f.write('LAST\tSenwiki\t"{page_title}"\n'.format(
                        page_title=re.sub(r'^.*/', '', episode.title_url)))

    elif args.COMMAND == 'follows':

        all_episodes = []
        wd = {}
        for URL, SEASON in SEASONS:
            season_wd = get_episodes_from_wikidata(SEASON)
            for key in season_wd.keys():
                if key in wd:
                    fmt = 'Multiple episodes called {0} found'
                    raise Exception(fmt.format(key))
                wd[key] = season_wd[key].getID()
            for episode in get_episodes_from_wikipedia(URL):
                all_episodes.append(episode)

        for before, current, after in previous_and_next(all_episodes):
            if before:
                f.write('{item_wd}\tP155\t{previous_wd}\n'.format(
                    item_wd=wd[current.title],
                    previous_wd=wd[before.title],
                ))
            if after:
                f.write('{item_wd}\tP156\t{next_wd}\n'.format(
                    item_wd=wd[current.title],
                    next_wd=wd[after.title],
                ))

    elif args.COMMAND == 'has-part':

        for URL, SEASON in SEASONS:
            wp = get_episodes_from_wikipedia(URL)
            wd = get_episodes_from_wikidata(SEASON)

            for episode in wp:
                f.write('{season_wd}\tP527\t{episode_wd}\n'.format(
                    season_wd=SEASON,
                    episode_wd=wd[episode.title].getID(),
                ))

    elif args.COMMAND == 'prod-code':
        for URL, SEASON in SEASONS:
            wp = get_episodes_from_wikipedia(URL)
            wd = get_episodes_from_wikidata(SEASON)

            for episode in wp:
                f.write('{episode_wd}\tP2364\t"{code}"\tS4656\t"{wiki_url}"\n'.format(
                    episode_wd=wd[episode.title].getID(),
                    code=episode.production_code,
                    wiki_url=URL,
                ))
