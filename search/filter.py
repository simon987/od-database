import os

from fold_to_ascii.fold_to_ascii import mapping


class SearchFilter:

    def __init__(self):

        self.blacklisted_terms = set()
        self.table = str.maketrans(dict(mapping.translate_table))

        if os.path.exists("search_blacklist.txt"):
            with open("search_blacklist.txt") as f:
                self.blacklisted_terms.update(line.strip() for line in f.readlines() if line[0] != "#" and line.strip())

    def should_block(self, query) -> bool:

        query = query.translate(self.table)
        query = query.lower()

        for raw_token in query.split():

            token = raw_token.strip("\"'/\\").strip()
            if token in self.blacklisted_terms:
                return True

        return False
