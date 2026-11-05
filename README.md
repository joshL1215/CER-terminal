Ultra simplified system design summary:

- We have RSS feeds stored in a yaml file
- A daily cron job (using GitHub Actions) runs some code including:
    - Parsing the yaml file to get rss feeds
    - interacting with our Supabase database to store new articles
    - calling an LLM API to pick which articles to keep based on relevancy rules in another yaml file
    - interacting with the database again to store these classifications

- Supabase provides an API for a frontend to do read-only queries on the information we accumulated
- On the frontend, a user will have a nice interface to scroll through a feed of only relevant article links
  
