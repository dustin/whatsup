update users set active=1 where active='t';
update users set active=0 where active='f';
update watches set active=0 where active='f';
update watches set active=1 where active='t';
update patterns set positive=1 where positive='t';
update patterns set positive=0 where positive='f';

update watches set last_update = replace(substr(last_update, 1, 19), 'T', ' ');
update watches set quiet_until = null;
update users set quiet_until = null;
