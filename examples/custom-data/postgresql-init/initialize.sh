#!/bin/bash
cat <<EOF | psql
create database quotes;
\c quotes
create table quotes ( id serial primary key, speaker varchar(30), quote varchar(200) );
insert into quotes (speaker, quote) values ( 'Groucho', 'Outside of a dog, a book is man''s best friend. Inside of a dog, it''s too dark to read.' );
insert into quotes (speaker, quote) values ( 'Groucho', 'From the moment I picked up your book until I laid it down, I was convulsed with laughter. 
Some day I intend reading it.' );
insert into quotes (speaker, quote) values ( 'Groucho', 'Go, and never darken my towels again.' );
insert into quotes (speaker, quote) values ( 'Groucho', 'Those are my principles, and if you don''t like them... well, I have others.' );
insert into quotes (speaker, quote) values ( 'Harpo', 'honk, honk' );
insert into quotes (speaker, quote) values ( 'Chico', 'Come get your ice-cream! Come get your tootsie-frootsie ice cream!' );
insert into quotes (speaker, quote) values ( 'Groucho', 'Captain Yard of the Scotland Spalding' );
insert into quotes (speaker, quote) values ( 'Chico', 'Who are you going to believe, me or your own eyes?' );
insert into quotes (speaker, quote) values ( 'Groucho', 'Thats no way to go into a speakeasy thats the way to go out' );
grant select, insert, update, delete on all tables in schema public to public;
grant all on all sequences in schema public to public;
EOF
