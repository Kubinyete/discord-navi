CREATE DATABASE IF NOT EXISTS navibotdb;
USE navibotdb;

-- CORE: Settings per guild based on a key, value approach 
-- Example: 
-- gui_id       gst_key             gst_value       gst_value_type
-- 999999999    allow_nsfw          no              1
-- 999999999    disable_command     yandere         0
-- 999999999    disable_command     osu             0
-- 999999999    welcome_message     Olá {member}!   0
CREATE TABLE guild_settings (
    gui_id BIGINT UNSIGNED NOT NULL PRIMARY KEY,
    gst_key VARCHAR(64) NOT NULL,
    gst_value VARCHAR(256) NOT NULL,
    gst_value_type TINYINT UNSIGNED NOT NULL DEFAULT 0
);

-- PROGRESSION: Keeps track of member experience, level is calculated during runtime
CREATE TABLE member (
    usr_id BIGINT UNSIGNED NOT NULL PRIMARY KEY,
    gui_id BIGINT UNSGINED NOT NULL PRIMARY KEY,
    usr_exp BIGINT UNSIGNED NOT NULL DEFAULT 0,
    usr_credits INT UNSIGNED NOT NULL DEFAULT 0
);

-- PROGRESSION: Global rewards that can be selected by the guild owner/administrator
CREATE TABLE bot_rewards (
    brw_id TINYINT UNSIGNED NOT NULL PRIMARY KEY,
    brw_enabled TINYINT(1) UNSIGNED NOT NULL DEFAULT 1,
    brw_reward_function VARCHAR(64) NOT NULL
);

-- PROGRESSION: Identifies which rewards are selected on a certain guild
CREATE TABLE guild_rewards (
    gui_id BIGINT UNSIGNED NOT NULL PRIMARY KEY,
    grw_name VARCHAR(64) NOT NULL,
    grw_description VARCHAR(256),
    grw_credits INT UNSIGNED NOT NULL DEFAULT 0,
    brw_id TINYINT UNSIGNED NOT NULL FOREIGN KEY REFERENCES bot_rewards(brw_id)
);