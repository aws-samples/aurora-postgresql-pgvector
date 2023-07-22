#!/bin/bash

export PGPASSWORD='<<password>>'; psql -h '<<Aurora DB Cluster host>>' -U '<<username>>' -d '<<DB Name>>' -p 5432
