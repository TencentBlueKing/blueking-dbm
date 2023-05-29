CREATE TABLE IF NOT EXISTS `users`(
    `id` INT UNSIGNED AUTO_INCREMENT,
    `name` VARCHAR(32) NOT NULL,
    `age` INT UNSIGNED NOT NULL,
    `address` VARCHAR(64) NOT NULL,
    `area` VARCHAR(32) NOT NULL,
	 `number` VARCHAR(64) NOT NULL,
   PRIMARY KEY ( `id` )
)ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `machines`(
    `id` INT UNSIGNED AUTO_INCREMENT,
    `type` VARCHAR(32) NOT NULL,
    `count` INT UNSIGNED NOT NULL,
    `created_at` timestamp NOT NULL,
    `updated_at` timestamp NOT NULL,
    PRIMARY KEY ( `id` )
)ENGINE=InnoDB DEFAULT CHARSET=utf8;