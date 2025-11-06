from ..web_crawl.generate_law import append_and_sort_file, search_law_by_name
from ..web_crawl.crawler import process_url as crawl_url
from .create_vector import process_df as vector_process_df
import os

def add_single_law(lawname: str, save_link: bool = True, save_csv: bool = True):
    """
    Adds a single URL to extract law data and insert it into the database.
    """
    try:
        law_link_result = search_law_by_name(lawname)
        if law_link_result is None:
            print(f"Law '{lawname}' not found.")
            return
        law_url = law_link_result['url']
        law_title = law_link_result['name']
        if save_link:
            append_and_sort_file(law_url)
            print(f"Saved link for law '{law_title}': {law_url}")

        df, filename = crawl_url(law_url)
        if save_csv:
            df.to_csv(os.path.join(os.path.dirname(__file__), "..", "web_crawl", "laws", "{}_{}.csv".format(filename, law_url.replace(":", "_").replace("/", "_").replace("?", "_"))),index=False)
            print(f"Saved CSV for law '{law_title}': {filename}_{law_url.replace(':', '_').replace('/', '_').replace('?', '_')}.csv")
        vector_process_df(df, filename)
    except Exception as e:
        print(f"Error adding law '{law_title}': {e}")
        return