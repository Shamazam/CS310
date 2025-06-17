-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Apr 19, 2025 at 12:00 PM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `chat_app`
--

-- --------------------------------------------------------

--
-- Table structure for table `active_chats`
--

CREATE TABLE `active_chats` (
  `tutorial_id` varchar(50) NOT NULL,
  `tutor_id` varchar(50) DEFAULT NULL,
  `start_time` datetime DEFAULT NULL,
  `duration_minutes` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `active_chats`
--

INSERT INTO `active_chats` (`tutorial_id`, `tutor_id`, `start_time`, `duration_minutes`) VALUES
('765', '9876', '2025-04-18 18:13:49', 30);

-- --------------------------------------------------------

--
-- Table structure for table `assignments`
--

CREATE TABLE `assignments` (
  `user_id` varchar(50) NOT NULL,
  `tutorial_id` varchar(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `assignments`
--

INSERT INTO `assignments` (`user_id`, `tutorial_id`) VALUES
('7982', '345'),
('7982333', '333'),
('7982333', '345'),
('8989', '765'),
('9876', '765'),
('jki', '122'),
('jkw', '122'),
('s11197324', '33333'),
('s11197324', '765');

-- --------------------------------------------------------

--
-- Table structure for table `tutorials`
--

CREATE TABLE `tutorials` (
  `id` varchar(50) NOT NULL,
  `name` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `tutorials`
--

INSERT INTO `tutorials` (`id`, `name`) VALUES
('122', 'uuuu'),
('333', 'fdf'),
('33333', 'mnm'),
('345', 'Test'),
('765', 'tutc'),
('84489', 'kbkbr'),
('9328', 'ncn');

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` varchar(50) NOT NULL,
  `name` varchar(100) DEFAULT NULL,
  `password_hash` varchar(255) DEFAULT NULL,
  `role` enum('admin','student','tutor') DEFAULT NULL,
  `profile_pic` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `name`, `password_hash`, `role`, `profile_pic`) VALUES
('0909', 'johnny', '$2b$12$lAyxWQiv5YSM7SN/cFk5fOLhuXLENSur9Szlrq1n1lh.GhG93TJym', 'student', NULL),
('7777', 'te', '$2b$12$EijB4UJ1jRJch4KTDQgs0eDz0OOFHeGddfIt2dtHrLL0hOVucf.Ni', 'tutor', NULL),
('789', 'bbch', '$2b$12$.TKKL0jWxHa.yCyW6hL/L.5g/iRyfYYXY4vEIYH.RaiFUjwWHkNfO', 'student', NULL),
('7982', 'bbch', '$2b$12$c.GZs8z84ZtT0FqzCkbyMebnt7uMFgjyF3CBaJAVEB1kPUW8HDphO', 'tutor', NULL),
('79823', 'bbch', '$2b$12$nx.aEvPipDxKqqBQzgkfoeCH3wEotZyLfVyj.kRmdsz3EqwjnsulG', 'tutor', NULL),
('798233', 'bbch', '$2b$12$rHeLvADxKQh0vyr7YaKcLORLUPH5yc1VyC0n2ZvjYBMY6Ivan9sH6', 'student', NULL),
('7982333', 'bbch', '$2b$12$NnvVZTASHjM6whoGZj8y6O0fMac7XxP3J.5q3wChAby8k4QL/AQUG', 'student', NULL),
('8989', 'Gyro', '$2b$12$bj3iIbPUKDw8WJkiKUy9.uJE0hgIjJ6sju23UuX8FXlKXHfLxLgBS', 'student', NULL),
('9876', 'ttut', '$2b$12$BxDdEwP2GY.8E9xL0W6/xuFg3mKzJkQ3ObSJFyLPtWUTfP0RvOwgG', 'tutor', NULL),
('99999', 'dszx', '$2b$12$bivAxfW1gPsIiTTwCEohm.xMa0xwBA2GC2Qp9n7z1MjoY0TY.RfGC', 'tutor', NULL),
('admin001', 'Super Admin', '$2b$12$aI87fVZNnct4jVHNiObBMu2MchbMfnAxWqBZyEmnitGlj49mbNFfe', 'admin', NULL),
('jki', 'kjdj', '$2b$12$f7yTlKhPfS3H/O4dcHvfRuypc9tglQd/oK4goMx8x3bKDNxqqt4Hm', 'tutor', NULL),
('jkw', 'mndn', '$2b$12$xSGLubwQ3Ws0J7zcIWIZe.H/xoesVLbCNDZNt94DxVQuF493aqt7S', 'student', NULL),
('s111973234', 'te', '$2b$12$1OLTVZacIbogxyBzfqRiteVg8Vda8ZXLV71d.bam3J3SeKQQl49yS', 'student', NULL),
('s11197324', 'jj', '$2b$12$Gnm9cJAm.JwXZG4dboTlYuwHVDSJBBRblfgmgJuqNCOFacJNBI82u', 'student', NULL),
('ss3749', 'ffkhf', '$2b$12$oSKRe.HT4O.nVEnAZ04h9.GLi/PST82Fu2g2Wipg3sL2C5sndvXq2', 'tutor', NULL);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `active_chats`
--
ALTER TABLE `active_chats`
  ADD PRIMARY KEY (`tutorial_id`),
  ADD KEY `tutor_id` (`tutor_id`);

--
-- Indexes for table `assignments`
--
ALTER TABLE `assignments`
  ADD PRIMARY KEY (`user_id`,`tutorial_id`),
  ADD KEY `tutorial_id` (`tutorial_id`);

--
-- Indexes for table `tutorials`
--
ALTER TABLE `tutorials`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`);

--
-- Constraints for dumped tables
--

--
-- Constraints for table `active_chats`
--
ALTER TABLE `active_chats`
  ADD CONSTRAINT `active_chats_ibfk_1` FOREIGN KEY (`tutorial_id`) REFERENCES `tutorials` (`id`),
  ADD CONSTRAINT `active_chats_ibfk_2` FOREIGN KEY (`tutor_id`) REFERENCES `users` (`id`);

--
-- Constraints for table `assignments`
--
ALTER TABLE `assignments`
  ADD CONSTRAINT `assignments_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
  ADD CONSTRAINT `assignments_ibfk_2` FOREIGN KEY (`tutorial_id`) REFERENCES `tutorials` (`id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
