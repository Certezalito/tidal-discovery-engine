# Fed into Gemini 2.5 Pro

I need to build a prompt for an ai spec kit from my following prompt.  It needs to make three things: a constitution, spec, and plan.  

I need a project that connects to my Tidal library and selects a user specified amount of random favorite tracks.  

Then project will then connect to last fm and retrieve tracks that sound similar; this will be a user configured amount OR support the default amount from last fm. 

The project will then take those tracks from last fm and put them into a tidal playlist.

When the project creates the playlist, it will be a user specfied name 

When the project creates a playlist, it will update the description of the playlist with the run date and other details. 

When the project creates a playlist it will go into a user specfied folder name.

The project shall use a .env for credentials 

The project shall use only credentials that are necessary. e.g. last fm doesn't require authentication for all api endpoints

The project shall use uv

The project shall be cli based

The readme shall be updated as features change or are updated

The project shall log the tracks retrievied and the playlist created.  Additionally the tracks put into the playlist shall be logged.

The project will be scheduled to run periodically and thus ideally needs to be non-interactive authentication