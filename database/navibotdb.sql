CREATE DATABASE IF NOT EXISTS navibotdb;
USE navibotdb;

-- CORE: Settings per guild based on a key, value approach 
-- Example: 
-- gui_id	   gst_key			 gst_value	   gst_value_type
-- 999999999	allow_nsfw		  no			  1
-- 999999999	disable_command	 yandere		 0
-- 999999999	disable_command	 osu			 0
-- 999999999	welcome_message	 Olá {member}!   0
CREATE TABLE guild_settings (
	gui_id BIGINT UNSIGNED NOT NULL,
	gst_key VARCHAR(64) NOT NULL,
	gst_value VARCHAR(256) NOT NULL,
	gst_value_type TINYINT UNSIGNED NOT NULL DEFAULT 0,
	PRIMARY KEY (gui_id, gst_key)
);

-- PROGRESSION: Keeps track of member experience, level is calculated during runtime
CREATE TABLE member (
	usr_id BIGINT UNSIGNED NOT NULL,
	gui_id BIGINT UNSIGNED NOT NULL,
	mem_exp BIGINT UNSIGNED NOT NULL DEFAULT 0,
	mem_credits INT UNSIGNED NOT NULL DEFAULT 0,
	mem_description VARCHAR(512),
	PRIMARY KEY (usr_id, gui_id)
);