from itertools import tee, islice, chain
import re

import attr
from bs4 import BeautifulSoup
from cached_property import cached_property
import requests


def previous_and_next(some_iterable):
    prevs, items, nexts = tee(some_iterable, 3)
    prevs = chain([None], prevs)
    nexts = chain(islice(nexts, 1, None), [None])
    return zip(prevs, items, nexts)


def rewrite_header(s):
    normalized_spaces = re.sub(r'(?ms)\s+', ' ', s)
    return re.sub(r'\s*\[.*', '', normalized_spaces)

@attr.s
class EpisodeTable(object):
    table_soup = attr.ib()

    @cached_property
    def heading_to_index(self):
        return {
            rewrite_header(th.text): i
            for i, th in enumerate(
                    self.table_soup.find('tr').find_all('th'))}

    @cached_property
    def rows(self):
        return [
            EpisodeRow(table=self, row_soup=tr)
            for tr in self.table_soup.find_all('tr')[1:]
            if not tr.find('td', class_='description')
        ]

    def __getitem__(self, index):
        return self.rows[index]


@attr.s
class EpisodeRow(object):
    table = attr.ib(repr=False)
    row_soup = attr.ib(repr=False)

    @cached_property
    def cells(self):
        return self.row_soup.find_all(['th', 'td'])

    @cached_property
    def title_cell(self):
        return self.cells[self.table.heading_to_index['Title']]

    @cached_property
    def title(self):
        m = re.search(r'"([^"]*)"(&\#160;\(Part[ ].\))?', self.title_cell.text)
        if not m:
            fmt = 'Unexpected format of cell text: {0}'
            raise Exception(fmt.format(self.title_cell.text))
        result = m.group(1)
        if m.group(2):
            result += m.group(2).replace('&#160;', ' ')
        return result

    @cached_property
    def title_url(self):
        a = self.title_cell.find('a')
        if a:
            return a['href']

    def cell(self, header):
        return self.cells[self.table.heading_to_index[header]]

    @cached_property
    def number_overall(self):
        return int(self.cell('No. overall').text.split()[0])

    @cached_property
    def number_in_season(self):
        return int(self.cell('No. in season').text.split()[0])

    @cached_property
    def production_code(self):
        return self.cell('Prod. code').text.split()[0]

    def __repr__(self):
        fmt = u"EpisodeRow(title='{0}' number_overall='{1}' number_in_season='{2}'"
        return fmt.format(self.title, self.number_overall, self.number_in_season)


def get_episodes_from_wikipedia(url):
    content = requests.get(url).text
    soup = BeautifulSoup(content, 'html.parser')
    table = EpisodeTable(soup.find(class_='wikiepisodetable'))
    return [episode for episode in table]


def get_episodes_from_wikidata(id):
    query = '''
SELECT ?itemLabel ?item ?series ?episodeNumber ?previousEpisode ?nextEpisode WHERE {
  BIND(wd:''' + id + ''' as ?season) .
  ?item wdt:P361 ?season .
  ?season wdt:P179 ?series .
  ?item p:P179 ?episodePartOfSeriesStatement .
  ?episodePartOfSeriesStatement ps:P179 ?series .
  OPTIONAL {
    ?episodePartOfSeriesStatement pq:P1545 ?episodeNumber
  }
  OPTIONAL {
    ?item wdt:P155 ?previousEpisode .
  }
  OPTIONAL {
    ?item wdt:P156 ?nextEpisode .
  }
  SERVICE wikibase:label {
     bd:serviceParam wikibase:language "en" .
  }
}
ORDER BY xsd:integer(?episodeNumber)
    '''
    episodes = {}
    for e in pg.WikidataSPARQLPageGenerator(query, site=site):
        e.get()
        title = e.labels['en']
        episodes[title] = e
    return episodes
