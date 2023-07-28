.PHONY: data/paper_litsing.tsv

data/paper_litsing.tsv:
	mkdir -p data
	curl -L "https://docs.google.com/spreadsheets/d/1DFdXA98bYPzK5Gf0M_PbNu3opvO-DIcrv7TMP5ywTMk/export?format=tsv&gid=0" -o data/paper_listing.tsv
