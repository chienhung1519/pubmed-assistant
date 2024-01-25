from typing import List
import requests
import json
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from dataclasses import dataclass
from argparse import ArgumentParser


@dataclass
class Article:
    pubmed_id: str = None
    title: str = None
    abstract: str = None
    authors: str = None
    doi: str = None
    url: str = None


class PubmedSearcher:

    def __init__(self) -> None:
        self.db = "pubmed"
        self.base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def search_idlist(self, query: str, retmax: int = 20) -> List:
        """Searches for a query and returns a list of ids"""
        url = f"{self.base}/esearch.fcgi?db={self.db}&term={query}&retmode=json&retmax={retmax}"
        result = requests.get(url)
        result = json.loads(result.text)
        idlist = result["esearchresult"]["idlist"]
        return idlist
    
    def concat_abstract(self, tree: ET) -> str:
        """Concatenates all abstract texts in a tree. Returns None if no abstract is found."""
        if tree.find("Article/Abstract") is None:
            return None
        abstract = ""
        for abstract_text in tree.findall("Article/Abstract/AbstractText"):
            abstract += f"{abstract_text.get('Label')}\n" if "Label" in abstract_text.attrib else ""
            abstract += abstract_text.text
        return abstract
    
    def concat_authors(self, tree: ET) -> str:
        """Concatenates all authors in a tree"""
        if tree.find("Article/AuthorList") is None:
            return None
        authors = ""
        for author in tree.findall("Article/AuthorList/Author"):
            lastname = author.find("LastName").text
            forename = author.find("ForeName").text
            authors += f"{lastname} {forename}, "
        return authors[:-2]
    
    def xml_to_articles(self, tree: ET) -> List[Article]:
        """Converts an xml tree to a list of Article class"""
        articles = []
        xml_articles = tree.findall("PubmedArticle/MedlineCitation")
        for xml_article in xml_articles:
            try:
                id = xml_article.find("PMID").text
                title = xml_article.find("Article/ArticleTitle").text
                abstract = self.concat_abstract(xml_article)
                authors = self.concat_authors(xml_article)
                doi = tree.find("Article/ELocationID").text
                url = f"https://pubmed.ncbi.nlm.nih.gov/{id}"
                articles.append(Article(id, title, abstract, authors, doi, url))
            except:
                continue
        return articles
    
    def search(self, query: str, retmax: int = 20) -> List:
        """Searches for a query and returns a list of articles"""
        idlist = self.search_idlist(query, retmax)
        url = f"{self.base}/efetch.fcgi?db={self.db}&retmode=xml&id={','.join(idlist)}&retmode=xml"
        result = requests.get(url)
        tree = ET.fromstring(result.text.encode("utf-8"))
        articles = self.xml_to_articles(tree)
        return articles
    
if __name__ == "__main__":
    # Arguments
    args = ArgumentParser()
    args.add_argument("--query", type=str, default="ChatGPT", help="Query to search")
    args.add_argument("--retmax", type=int, default=20, help="Maximum number of articles to return")
    args = args.parse_args()
    
    # Search
    searcher = PubmedSearcher()
    articles = searcher.search(args.query, args.retmax)
    for article in articles:
        print(article, "\n")
        print()