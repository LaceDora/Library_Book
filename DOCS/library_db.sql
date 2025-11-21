-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: localhost
-- Generation Time: Nov 20, 2025 at 08:44 AM
-- Server version: 10.4.28-MariaDB
-- PHP Version: 8.0.28

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `library_db`
--

-- --------------------------------------------------------

--
-- Table structure for table `audit`
--

CREATE TABLE `audit` (
  `id` int(11) NOT NULL,
  `action` varchar(50) NOT NULL,
  `actor_user_id` int(11) DEFAULT NULL,
  `target_borrow_id` int(11) DEFAULT NULL,
  `target_book_id` int(11) DEFAULT NULL,
  `timestamp` datetime NOT NULL DEFAULT current_timestamp(),
  `details` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `book`
--

CREATE TABLE `book` (
  `id` int(11) NOT NULL,
  `title` varchar(150) NOT NULL,
  `author` varchar(100) NOT NULL,
  `description` text DEFAULT NULL,
  `image_url` varchar(255) DEFAULT NULL,
  `quantity` int(11) NOT NULL DEFAULT 1,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `views_count` int(11) NOT NULL DEFAULT 0,
  `category` varchar(50) DEFAULT NULL,
  `available_quantity` int(11) NOT NULL DEFAULT 1,
  `created_at` datetime DEFAULT current_timestamp(),
  `views` int(11) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `book`
--

INSERT INTO `book` (`id`, `title`, `author`, `description`, `image_url`, `quantity`, `is_active`, `views_count`, `category`, `available_quantity`, `created_at`, `views`) VALUES
(1, 'Clean Code', 'Robert C. Martin', 'hello\r\n', 'https://bukharibooks.com/wp-content/uploads/2021/10/clean-code.png', 5, 1, 0, 'Lập trình', 5, '2025-10-26 02:47:17', 0),
(2, 'Fluent Python', 'Luciano Ramalho', 'hi', 'https://www.oreilly.com/covers/urn:orm:book:9781491946237/400w/', 4, 1, 0, 'Lập trình', 4, '2025-10-26 02:47:17', 0),
(3, 'Automate the Boring Stuff', 'Al Sweigart', 'hi', 'https://static-ppimages.freetls.fastly.net/nielsens/9781593279929.jpg?canvas=600,600&fit=bounds&height=600&mode=max&width=600&404=default.jpg', 5, 1, 0, 'Lập trình', 5, '2025-10-26 02:47:17', 0),
(4, 'Âm nhạc cổ điển cho người mới bắt đầu', 'Julian Johnson', NULL, 'https://images-eu.ssl-images-amazon.com/images/I/61J-HZvJHDL._AC_UL600_SR600,600_.jpg', 4, 1, 0, 'Âm nhạc', 4, '2025-10-26 02:47:17', 0),
(5, 'Guitar cơ bản', 'Tạ Tấn', NULL, 'https://cdn1.fahasa.com/media/catalog/product/h/h/hh_bia-1_phuongphap-hoc-ghita-phan-co-ban.jpg', 3, 1, 0, 'Âm nhạc', 3, '2025-10-26 02:47:17', 0),
(6, 'Nhạc Lý Căn Bản', 'Nguyễn Hạnh', NULL, 'https://cdn1.fahasa.com/media/catalog/product/i/m/image_231334.jpg', 2, 1, 0, 'Âm nhạc', 2, '2025-10-26 02:47:17', 0),
(7, 'Piano cho thiếu nhi', 'Lê Dũng', NULL, 'https://tokhaiyte.vn/wp-content/uploads/2024/05/piano-cho-thieu-nhi-tuyen-tap-220-tieu-pham-noi-tieng-phan-2-kem-file-audio-pdf-1.jpg', 5, 1, 0, 'Âm nhạc', 5, '2025-10-26 02:47:17', 0),
(8, 'Kỹ thuật ghi âm', 'Phạm Xuân Ánh', NULL, 'https://online.anyflip.com/mdhby/bjmv/files/mobile/1.jpg?1656055702', 2, 1, 0, 'Âm nhạc', 2, '2025-10-26 02:47:17', 0),
(9, 'Lập trình Python nâng cao', 'Dr. Gabriele Lanaro, Quan Nguyen, Sakis Kasampalis', NULL, 'https://www.oreilly.com/library/cover/9781838551216/1200w630h/', 3, 1, 0, 'Lập trình', 3, '2025-10-26 02:47:17', 0),
(10, 'JavaScript hiện đại', 'Brad Traversy', NULL, 'https://www.oreilly.com/library/cover/9781805127826/1200w630h/', 4, 1, 0, 'Lập trình', 4, '2025-10-26 02:47:17', 0),
(11, 'Mạng máy tính', 'S. Tanenbaum', NULL, 'https://images-eu.ssl-images-amazon.com/images/I/71EpQCiJXKL._AC_UL600_SR600,600_.jpg', 2, 1, 0, 'Lập trình', 2, '2025-10-26 02:47:17', 0),
(12, 'Lập trình Web với Flask', 'Miguel Grinberg', NULL, 'https://www.oreilly.com/covers/urn:orm:book:9781491947586/400w/', 5, 1, 0, 'Lập trình', 5, '2025-10-26 02:47:17', 0),
(13, 'Cấu trúc dữ liệu và giải thuật', 'Narasimha Karumanchi', NULL, 'https://images-eu.ssl-images-amazon.com/images/I/61mF67j52OL._AC_UL600_SR600,600_.jpg', 3, 1, 0, 'Lập trình', 3, '2025-10-26 02:47:17', 0),
(14, 'One Piece - Tập 1', 'Eiichiro Oda', NULL, 'https://bizweb.dktcdn.net/thumb/grande/100/441/742/products/one-piece-bia-tap-1-tb-2025.jpg?v=1748768786133', 6, 1, 0, 'Truyện tranh', 6, '2025-10-26 02:47:17', 0),
(15, 'Naruto - Tập 1', 'Masashi Kishimoto', NULL, 'https://product.hstatic.net/200000122283/product/naruto---tap-1---tb-2022_986f7449ef3545babf33ee7bae1c7aeb_master.jpg', 5, 1, 0, 'Truyện tranh', 5, '2025-10-26 02:47:17', 0),
(16, 'Doraemon - Tuyển tập', 'Fujiko F', NULL, 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRtP2Ckol5vleBbCOE3fcXNpyD6r2usdcqH8g&s', 4, 1, 0, 'Truyện tranh', 4, '2025-10-26 02:47:17', 0),
(17, 'Attack on Titan - Tập 1', 'Hajime Isayama', NULL, 'https://product.hstatic.net/200000301138/product/dai_chien_titan_tap_1_a601184cf2494a10ba1e18b557d82211_f96ef635f2764d7194c618176b83afc1_1024x1024.jpg', 3, 1, 0, 'Truyện tranh', 3, '2025-10-26 02:47:17', 0),
(18, 'Dragon Ball - Tập 1', 'Akira Toriyama', NULL, 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR-Gy_qXnoOH4W3AqHGvsnHMxZnzsuJ81MI8g&s', 4, 1, 0, 'Truyện tranh', 4, '2025-10-26 02:47:17', 0),
(19, 'Giải phẫu học', 'TS. BS. Nguyễn Hoàng Vũ', NULL, 'https://gmhs.vn/wp-content/uploads/2025/02/giai-phau-hoc-tap-1-chuong-trinh-doi-moi-dhyd-tphcm.jpg', 2, 1, 0, 'Y học', 2, '2025-10-26 02:47:17', 0),
(20, 'Thực Vật Dược', 'PGS.TS. Trần Văn Ơn', NULL, 'https://lh4.googleusercontent.com/proxy/UVJ97arhnJhB6_rgXnj5FfZh6UsT7nS53GEdXETwfLysqNFCSu4NPfvavmGMYre9kfqzEia4e2nwLkjEgVM2oBVHne9irdCxrRkw_aGEI2DxQ0wP__aBUh6vY40E3bfFLNU5v-fsEpQQf6bu7oiYtdBL8tByal4PWhiReQ', 2, 1, 0, 'Y học', 2, '2025-10-26 02:47:17', 0),
(21, 'Hướng dẫn chẩn đoán lâm sàng', 'Lương y Nguyễn Thiên Quyến', NULL, 'https://tokhaiyte.vn/wp-content/uploads/2024/10/kinh-nghiem-de-tranh-sai-lam-trong-chuan-doan-va-dieu-tri-dong-y-pdf.jpg', 1, 1, 0, 'Y học', 1, '2025-10-26 02:47:17', 0),
(22, 'Sức khỏe cộng đồng', 'Hoàng Y', NULL, 'https://vietbooks.info/attachments/upload_2021-8-17_21-8-49-png.1129/', 3, 1, 0, 'Y học', 3, '2025-10-26 02:47:17', 0),
(23, 'Nhồi Máu Cơ Tim Và Cách Tự Cứu Mình', 'ThS BS CKII Võ Anh Minh', NULL, 'https://cdn1.fahasa.com/media/catalog/product/9/7/9786326041910.jpg', 2, 1, 0, 'Y học', 2, '2025-10-26 02:47:17', 0),
(24, 'Tâm lý học ứng dụng', 'Patrick King', NULL, 'https://cdn1.fahasa.com/media/catalog/product/i/m/image_239223.jpg', 5, 1, 0, 'Tâm lý', 5, '2025-10-26 02:47:17', 0),
(25, 'Thấu hiểu bản thân', 'Osho', NULL, 'https://sachtiengviet.com/cdn/shop/files/9d9dcf9eb2499f3476d4a0de29a529ac.jpg?v=1719043041', 5, 1, 0, 'Tâm lý', 5, '2025-10-26 02:47:17', 0),
(26, 'Giao tiếp hiệu quả', 'Lý Nam', NULL, 'https://masterihomes.com.vn/wp-content/uploads/2025/08/b_a-1-k_-n_ng-giao-ti_p-hi_u-qu__1-510x510.jpg', 3, 1, 0, 'Tâm lý', 3, '2025-10-26 02:47:17', 0),
(27, 'Quản lý cảm xúc', 'Steven Sloman', NULL, 'https://cdn1.fahasa.com/media/catalog/product/2/0/2022000000070.jpg', 6, 1, 1, 'Tâm lý', 6, '2025-10-26 02:47:17', 0),
(28, 'Tâm lý trẻ em', 'Trương Binh', NULL, 'https://product.hstatic.net/1000237375/product/thau-hieu-tam-ly-tre-900x900_1_b5d98c353f294aada4d2069eb9b0b2b0_master.png', 5, 1, 0, 'Tâm lý', 5, '2025-10-26 02:47:17', 0);

-- --------------------------------------------------------

--
-- Table structure for table `borrow`
--

CREATE TABLE `borrow` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `book_id` int(11) NOT NULL,
  `borrow_date` datetime NOT NULL DEFAULT current_timestamp(),
  `book_title` varchar(150) DEFAULT NULL,
  `return_date` datetime DEFAULT NULL,
  `return_condition` varchar(20) DEFAULT NULL,
  `return_notes` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `user`
--

CREATE TABLE `user` (
  `id` int(11) NOT NULL,
  `username` varchar(80) NOT NULL,
  `password_hash` varchar(500) NOT NULL,
  `is_admin` tinyint(1) NOT NULL DEFAULT 0,
  `student_staff_id` varchar(20) NOT NULL,
  `role` varchar(20) NOT NULL,
  `avatar_url` varchar(255) DEFAULT NULL,
  `email` varchar(120) DEFAULT NULL,
  `phone` varchar(30) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `user`
--

INSERT INTO `user` (`id`, `username`, `password_hash`, `is_admin`, `student_staff_id`, `role`, `avatar_url`, `email`, `phone`) VALUES
(16, 'Phan Quốc Huy', 'bf6a51aa366add6b60a2c18e326a71e9e89eec0ca1df2bf9ea32754950334bb7c2758c644a69931fadf1ef75bf9bb68b321db68283df780bfb09eae6dfddcf4d', 0, '2331540092', 'student', NULL, NULL, NULL),
(17, 'Quản Thư 1', '3c13b7a75c1606cf99d80d57e1633333b04edc7d6a7efbee3f6f3c4ce3548999e9b7ff47b8e4f2ec020e0eee6b9f9457ae46fadaa3d04c213775ebb0292bc17f', 1, 'ADMIN01', 'staff', '/static/uploads/user_17_avatar_1762497695.jpeg', NULL, NULL),
(18, 'Nguyễn Minh Thuận', 'de82fc83a861e856f11bfff6a18a3665fa3af08c331911cbd40948b7d2392385dbc2f21bc5051c4a999190c9ffaf7f219d2b671929103c282e54bb903dedb49e', 0, '12345678', 'staff', NULL, NULL, NULL);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `audit`
--
ALTER TABLE `audit`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_audit_actor` (`actor_user_id`),
  ADD KEY `idx_audit_borrow` (`target_borrow_id`),
  ADD KEY `idx_audit_book` (`target_book_id`);

--
-- Indexes for table `book`
--
ALTER TABLE `book`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `borrow`
--
ALTER TABLE `borrow`
  ADD PRIMARY KEY (`id`),
  ADD KEY `fk_borrow_user_idx` (`user_id`),
  ADD KEY `fk_borrow_book_idx` (`book_id`);

--
-- Indexes for table `user`
--
ALTER TABLE `user`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `student_staff_id` (`student_staff_id`),
  ADD UNIQUE KEY `unique_email` (`email`),
  ADD UNIQUE KEY `unique_phone` (`phone`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `audit`
--
ALTER TABLE `audit`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `book`
--
ALTER TABLE `book`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=32;

--
-- AUTO_INCREMENT for table `borrow`
--
ALTER TABLE `borrow`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `user`
--
ALTER TABLE `user`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=19;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `borrow`
--
ALTER TABLE `borrow`
  ADD CONSTRAINT `fk_borrow_book` FOREIGN KEY (`book_id`) REFERENCES `book` (`id`) ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_borrow_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON UPDATE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
