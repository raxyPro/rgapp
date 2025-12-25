the site is hosted on raygrowcs.com
in public_html folder
there is index.html file 
the directory in production host wordpress site so renaming the index.html will make wordress site work



Note for Production
Important note (so you don’t get stuck again)
In run_migrations_online() you’re using:
poolclass=pool.NullPool
That’s fine for development and avoids stale connections, but later you can switch back to a pooled config.