# Web Crawl

## Step 1 (Optional):

first copy the div that contains the links that you want to crawl, put it in `div.txt`

After running 
```bash
python get_link_from_div.py| sort -u | tee links.txt
```

you will get a links.txt file that contains all the links that you want to crawl

## Step 2: Crawl to csv (and files):

Run `python crawler.py`

You will get `./laws` which contains csv including actname, chapter, article_no, and content for each law

and `./pdfs`, which contains other files that are not able to convert to csv (my program will assume that it is pdf)
