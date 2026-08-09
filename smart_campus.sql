-- MySQL dump 10.13  Distrib 8.0.39, for Win64 (x86_64)
--
-- Host: localhost    Database: smart_campus
-- ------------------------------------------------------
-- Server version	8.0.39

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Current Database: `smart_campus`
--

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `smart_campus` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;

USE `smart_campus`;

--
-- Table structure for table `ai_dialog_summaries`
--

DROP TABLE IF EXISTS `ai_dialog_summaries`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ai_dialog_summaries` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` int NOT NULL,
  `summary` text NOT NULL,
  `level` enum('NORMAL','MILD','MODERATE','SEVERE') NOT NULL,
  `keywords_matched` varchar(200) DEFAULT NULL,
  `raw_snippet` text,
  `resolved` tinyint(1) NOT NULL,
  `created_at` datetime NOT NULL,
  `intervention_type` enum('TALK','PARENT_MEETING','PSYCHOLOGY_REFERRAL','OTHER') DEFAULT NULL,
  `intervention_note` text,
  `resolved_by` int DEFAULT NULL,
  `resolved_at` datetime DEFAULT NULL,
  `follow_up_date` date DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_ai_dialog_summaries_student_id` (`student_id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ai_dialog_summaries`
--

LOCK TABLES `ai_dialog_summaries` WRITE;
/*!40000 ALTER TABLE `ai_dialog_summaries` DISABLE KEYS */;
INSERT INTO `ai_dialog_summaries` VALUES (1,10,'学生表示近期学习压力大，有焦虑情绪，睡眠质量不佳','MILD','焦虑,失眠',NULL,0,'2026-07-20 18:22:04',NULL,NULL,NULL,NULL,NULL),(2,10,'学生在对话中提到对未来的迷茫，情绪低落','NORMAL','迷茫',NULL,1,'2026-07-20 18:22:04',NULL,NULL,NULL,NULL,NULL),(3,13,'学生多次提到失眠、焦虑，对考试感到极度恐慌，建议重点关注','MODERATE','失眠,焦虑,考试',NULL,0,'2026-07-20 18:22:04',NULL,NULL,NULL,NULL,NULL),(4,13,'学生表示\"觉得活着没意思\"，触发高危关键词，已立即通知辅导员','SEVERE','没意思,活着',NULL,0,'2026-07-20 18:22:04',NULL,NULL,NULL,NULL,NULL);
/*!40000 ALTER TABLE `ai_dialog_summaries` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `alembic_version`
--

DROP TABLE IF EXISTS `alembic_version`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `alembic_version` (
  `version_num` varchar(32) NOT NULL,
  PRIMARY KEY (`version_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `alembic_version`
--

LOCK TABLES `alembic_version` WRITE;
/*!40000 ALTER TABLE `alembic_version` DISABLE KEYS */;
INSERT INTO `alembic_version` VALUES ('ef8ceac9af06');
/*!40000 ALTER TABLE `alembic_version` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `announcement_reads`
--

DROP TABLE IF EXISTS `announcement_reads`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `announcement_reads` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` int NOT NULL,
  `announcement_id` int NOT NULL,
  `read_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_student_announcement` (`student_id`,`announcement_id`),
  KEY `ix_announcement_reads_student_id` (`student_id`),
  KEY `ix_announcement_reads_announcement_id` (`announcement_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `announcement_reads`
--

LOCK TABLES `announcement_reads` WRITE;
/*!40000 ALTER TABLE `announcement_reads` DISABLE KEYS */;
/*!40000 ALTER TABLE `announcement_reads` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `campus_figures`
--

DROP TABLE IF EXISTS `campus_figures`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `campus_figures` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `title` varchar(100) NOT NULL,
  `avatar` varchar(255) NOT NULL,
  `description` text NOT NULL,
  `category` varchar(20) NOT NULL,
  `proofs` text,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `campus_figures`
--

LOCK TABLES `campus_figures` WRITE;
/*!40000 ALTER TABLE `campus_figures` DISABLE KEYS */;
INSERT INTO `campus_figures` VALUES (5,'陈慧敏','优秀辅导员','/images/avatar5.jpg','人工智能学院辅导员，从事学生工作10年','teacher',NULL);
/*!40000 ALTER TABLE `campus_figures` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `campus_impression_items`
--

DROP TABLE IF EXISTS `campus_impression_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `campus_impression_items` (
  `id` int NOT NULL AUTO_INCREMENT,
  `source` varchar(20) NOT NULL,
  `college_key` varchar(50) DEFAULT NULL,
  `title` varchar(200) NOT NULL,
  `image_url` varchar(500) DEFAULT NULL,
  `url` varchar(500) NOT NULL,
  `date` varchar(20) DEFAULT NULL,
  `fetched_at` varchar(30) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_campus_impression_items_college_key` (`college_key`),
  KEY `ix_campus_impression_items_source` (`source`)
) ENGINE=InnoDB AUTO_INCREMENT=6091 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `campus_impression_items`
--

LOCK TABLES `campus_impression_items` WRITE;
/*!40000 ALTER TABLE `campus_impression_items` DISABLE KEYS */;
INSERT INTO `campus_impression_items` VALUES (6028,'jwc_entries',NULL,'教务管理系统',NULL,'https://jwgl.mycc.edu.cn',NULL,'2026-08-10 01:13:06'),(6029,'jwc_entries',NULL,'实习管理系统',NULL,'https://xixunyun.com/login.html',NULL,'2026-08-10 01:13:06'),(6030,'jwc_entries',NULL,'实验管理平台',NULL,'https://syglxt.mycc.edu.cn/zxcas',NULL,'2026-08-10 01:13:06'),(6031,'jwc_entries',NULL,'超星在线学习平台',NULL,'https://44oldowe.mh.chaoxing.com/page/1164017/show',NULL,'2026-08-10 01:13:06'),(6032,'jwc_entries',NULL,'教学质量管理平台',NULL,'https://mycc.mycospxk.com',NULL,'2026-08-10 01:13:06'),(6033,'jwc_entries',NULL,'毕业论文(设计)管理系统',NULL,'https://cloud.fanyu.com/organ/lib/ccswust',NULL,'2026-08-10 01:13:06'),(6034,'jwc_entries',NULL,'教学校历',NULL,'https://jwc.mycc.edu.cn/jwgl/jxxl.htm',NULL,'2026-08-10 01:13:06'),(6035,'jwc_entries',NULL,'作息时间',NULL,'https://jwc.mycc.edu.cn/jwgl/zxsj.htm',NULL,'2026-08-10 01:13:06'),(6036,'jwc_entries',NULL,'课表查询',NULL,'https://jwc.mycc.edu.cn/jwgl/kbcx.htm',NULL,'2026-08-10 01:13:06'),(6037,'jwc_jxdt',NULL,'绵阳城市学院师生卫冕全国高等院校健身气功锦标赛两项冠军','https://jwc.mycc.edu.cn/__local/8/A6/29/21F534D65ADC5501569A9F07E5E_CC6D4707_EB77B.png','https://jwc.mycc.edu.cn/info/1012/3831.htm','2026-07-31','2026-08-10 01:13:06'),(6038,'jwc_jxdt',NULL,'绵阳城市学院基层教学管理人员教育教学能力提升集中培训圆满举行','https://jwc.mycc.edu.cn/__local/A/89/90/0995D19F9110034519156CE3932_A3FEDBDF_D7BCC.png','https://jwc.mycc.edu.cn/info/1012/3822.htm','2026-07-17','2026-08-10 01:13:06'),(6039,'jwc_jxdt',NULL,'赛场展风采，教学结硕果——我校教师在全国高校教学竞赛西南赛区喜获佳绩','https://jwc.mycc.edu.cn/__local/C/FF/2D/82255C4D1108C7C04C78693913C_28BD7167_18725.png','https://jwc.mycc.edu.cn/info/1012/3773.htm','2026-06-22','2026-08-10 01:13:06'),(6040,'jwc_jxdt',NULL,'绵阳城市学院2026年实验室安全知识竞赛圆满举办','https://jwc.mycc.edu.cn/__local/0/88/DC/4D9EE8D9179FF4E1DB1E37DAE17_9A644EB7_1DBA2.jpeg?e=.jpeg','https://jwc.mycc.edu.cn/info/1012/3761.htm','2026-06-12','2026-08-10 01:13:06'),(6041,'jwc_jxdt',NULL,'斩获196项大奖！我校5月大学生竞赛再创佳绩','https://jwc.mycc.edu.cn/__local/F/A5/1C/CD3D3221047DAE38C933920B534_3196837E_41E3A.png?e=.png','https://jwc.mycc.edu.cn/info/1012/3752.htm','2026-06-05','2026-08-10 01:13:06'),(6042,'jwc_jxdt',NULL,'我校成功举办“明德修身·匠心育人”师德师风与教学能力提升专题讲座','https://jwc.mycc.edu.cn/__local/4/0E/43/2AE8DD9D929915094F471ABD834_05EF13B7_371C1.png','https://jwc.mycc.edu.cn/info/1012/3700.htm','2026-05-27','2026-08-10 01:13:06'),(6043,'jwc_jxdt',NULL,'严师德红线正教风，抓规范管理夯根基 ——我校创意设计学院全面启动师德师风建设','https://jwc.mycc.edu.cn/__local/E/3F/34/EA17426785E6E48D6CF49009E52_3671D2A4_5BEE0.png','https://jwc.mycc.edu.cn/info/1012/3696.htm','2026-05-21','2026-08-10 01:13:06'),(6044,'jwc_jxdt',NULL,'锚定育人质量 深耕内涵建设——我校召开2023届、2025届毕业生中短期培养质量评价报告解读会','https://jwc.mycc.edu.cn/__local/E/0B/1B/C9684F8AF0CBC7589564B9D512A_3CF56440_16308.png','https://jwc.mycc.edu.cn/info/1012/3691.htm','2026-05-15','2026-08-10 01:13:06'),(6045,'jwc_jxdt',NULL,'我校教师在第六届四川省高校教师教学创新大赛中取得历史性突破','https://jwc.mycc.edu.cn/__local/8/23/EF/879C9DA74C7567A74BACE92D2B3_88F955DF_1DDEE.png?e=.png','https://jwc.mycc.edu.cn/info/1012/3671.htm','2026-05-09','2026-08-10 01:13:06'),(6046,'jwc_jxdt',NULL,'教育部备案获批!绵阳城市学院新增两个本科专业，学科专业建设迈上新台阶','https://jwc.mycc.edu.cn/__local/A/48/BD/FECF85B69780997D94516A36E04_D76F925D_DEF9.png','https://jwc.mycc.edu.cn/info/1012/3667.htm','2026-05-08','2026-08-10 01:13:06'),(6047,'jwc_tzgg',NULL,'绵阳城市学院关于2026-2027学年第一学期学生教材订购的通知',NULL,'https://jwc.mycc.edu.cn/info/1011/3841.htm','2026-08-01','2026-08-10 01:13:06'),(6048,'jwc_tzgg',NULL,'绵阳城市学院关于给予姬海鑫等23名学生学业降级的决定',NULL,'https://jwc.mycc.edu.cn/info/1011/3816.htm','2026-07-13','2026-08-10 01:13:06'),(6049,'jwc_tzgg',NULL,'绵阳城市学院关于公布2026-2027学年第一学期转专业学生名单的通知',NULL,'https://jwc.mycc.edu.cn/info/1011/3792.htm','2026-07-01','2026-08-10 01:13:06'),(6050,'jwc_tzgg',NULL,'绵阳城市学院关于领取2026年上半年补授学士学位证书的通知',NULL,'https://jwc.mycc.edu.cn/info/1011/3791.htm','2026-06-29','2026-08-10 01:13:06'),(6051,'jwc_tzgg',NULL,'绵阳城市学院关于开展2026-2027学年毕业实习重修工作的通知',NULL,'https://jwc.mycc.edu.cn/info/1011/3765.htm','2026-06-18','2026-08-10 01:13:06'),(6052,'jwc_tzgg',NULL,'绵阳城市学院关于开展2027届毕业实习工作的通知',NULL,'https://jwc.mycc.edu.cn/info/1011/3764.htm','2026-06-18','2026-08-10 01:13:06'),(6053,'jwc_tzgg',NULL,'绵阳城市学院关于2026年上半年CET、2026年TEM4考试期间教学活动调整及考场封闭管理的通知',NULL,'https://jwc.mycc.edu.cn/info/1011/3751.htm','2026-06-08','2026-08-10 01:13:06'),(6054,'jwc_tzgg',NULL,'绵阳城市学院关于2026年端午节放假期间教学安排的通知',NULL,'https://jwc.mycc.edu.cn/info/1011/3741.htm','2026-06-05','2026-08-10 01:13:06'),(6055,'jwc_tzgg',NULL,'绵阳城市学院关于开展2026年上半年补授学士学位申请工作的通知',NULL,'https://jwc.mycc.edu.cn/info/1011/3734.htm','2026-06-03','2026-08-10 01:13:06'),(6056,'jwc_tzgg',NULL,'绵阳城市学院关于对周燚等25名学生作退学处理的公示',NULL,'https://jwc.mycc.edu.cn/info/1011/3733.htm','2026-06-03','2026-08-10 01:13:06'),(6057,'jwc_gjxx',NULL,'实习实训基地建设',NULL,'https://jwc.mycc.edu.cn/jxjs/sxsxjdjs.htm',NULL,'2026-08-10 01:13:06'),(6058,'jwc_gjxx',NULL,'实习实训基地（校外实习实训）',NULL,'https://jwc.mycc.edu.cn/sjjx/sxsxjd_xwsxsx_.htm',NULL,'2026-08-10 01:13:06'),(6059,'jwc_gjxx',NULL,'实验室安全教育',NULL,'https://jwc.mycc.edu.cn/sjjx/sysaqjy.htm',NULL,'2026-08-10 01:13:06'),(6060,'jwc_gjxx',NULL,'毕业论文（设计）',NULL,'https://jwc.mycc.edu.cn/sjjx/bylw_sj_.htm',NULL,'2026-08-10 01:13:06'),(6061,'jwc_gjxx',NULL,'国家政策法规',NULL,'https://jwc.mycc.edu.cn/gzzd/gjzcfg.htm',NULL,'2026-08-10 01:13:06'),(6062,'jwc_gjxx',NULL,'校内规章制度',NULL,'https://jwc.mycc.edu.cn/gzzd/xngzzd.htm',NULL,'2026-08-10 01:13:06'),(6063,'jwc_gjxx',NULL,'实习实训基地建设',NULL,'https://jwc.mycc.edu.cn/jxjs/sxsxjdjs.htm',NULL,'2026-08-10 01:13:06'),(6064,'jwc_gjxx',NULL,'实习实训基地（校外实习实训）',NULL,'https://jwc.mycc.edu.cn/sjjx/sxsxjd_xwsxsx_.htm',NULL,'2026-08-10 01:13:06'),(6065,'jwc_gjxx',NULL,'实验室安全教育',NULL,'https://jwc.mycc.edu.cn/sjjx/sysaqjy.htm',NULL,'2026-08-10 01:13:06'),(6066,'jwc_gjxx',NULL,'毕业论文（设计）',NULL,'https://jwc.mycc.edu.cn/sjjx/bylw_sj_.htm',NULL,'2026-08-10 01:13:06'),(6067,'jwc_jxjs',NULL,'绵阳城市学院关于2026年康复治疗学专业申报情况的公示',NULL,'https://jwc.mycc.edu.cn/info/1021/3851.htm','2026-07-30','2026-08-10 01:13:06'),(6068,'jwc_jxjs',NULL,'绵阳城市学院关于开展首批校级应用型品牌专业（群）和微专业建设工作的通知',NULL,'https://jwc.mycc.edu.cn/info/1021/3821.htm','2026-07-17','2026-08-10 01:13:06'),(6069,'jwc_jxjs',NULL,'绵阳城市学院关于公布2026年第一批“一师一优课”课程建设项目结题验收结果的通知',NULL,'https://jwc.mycc.edu.cn/info/1022/3781.htm','2026-06-24','2026-08-10 01:13:06'),(6070,'jwc_jxjs',NULL,'绵阳城市学院关于2026年四川省高等教育高质量发展专项教学改革研究项目拟推荐名单的公示',NULL,'https://jwc.mycc.edu.cn/info/1020/3802.htm','2026-06-24','2026-08-10 01:13:06'),(6071,'jwc_jxjs',NULL,'绵阳城市学院关于开展2026年上半年校级教育教学改革研究项目结题验收及中期检查工作的通知',NULL,'https://jwc.mycc.edu.cn/info/1020/3742.htm','2026-06-05','2026-08-10 01:13:06'),(6072,'jwc_jxjs',NULL,'绵阳城市学院关于公布2026年微课项目立项名单的通知',NULL,'https://jwc.mycc.edu.cn/info/1020/3711.htm','2026-05-29','2026-08-10 01:13:06'),(6073,'jwc_jxjs',NULL,'绵阳城市学院关于公布2026年“一师一优课”课程建设项目立项的通知',NULL,'https://jwc.mycc.edu.cn/info/1022/3702.htm','2026-05-29','2026-08-10 01:13:06'),(6074,'jwc_jxjs',NULL,'绵阳城市学院关于2026年微课项目拟立项名单的公示',NULL,'https://jwc.mycc.edu.cn/info/1020/3695.htm','2026-05-20','2026-08-10 01:13:06'),(6075,'jwc_jxjs',NULL,'绵阳城市学院关于2026年“一师一优课”课程建设项目拟立项名单的公示',NULL,'https://jwc.mycc.edu.cn/info/1022/3692.htm','2026-05-20','2026-08-10 01:13:06'),(6076,'jwc_jxjs',NULL,'绵阳城市学院关于开展2026年第一批“一师一优课”课程建设项目结题工作的通知',NULL,'https://jwc.mycc.edu.cn/info/1022/3666.htm','2026-05-07','2026-08-10 01:13:06'),(6077,'college_news','马克思主义学院','喜报！我院教师寇壤斩获四川省高校“毛...6月13日，在四川省高校《毛泽东思想和中国特色社会主义理论体系概论》课程教学比赛中，我院教师寇壤与来自省内72所高校的优秀教师同台竞技，凭借扎实的教学功底、清晰的授课思路和创新的教学设计，斩获本科组特等...',NULL,'https://mksxy.mycc.edu.cn/info/1003/2627.htm',NULL,'2026-08-10 01:13:06'),(6078,'college_news','马克思主义学院','拥抱AI时代 共筑思政新篇——我院教师代表参加全...',NULL,'https://mksxy.mycc.edu.cn/info/1003/2714.htm',NULL,'2026-08-10 01:13:06'),(6079,'college_news','人工智能学院','人工智能学院女教师赴北川开展“三八”...',NULL,'https://xdjsxy.mycc.edu.cn/info/1008/2402.htm','2026.04.01','2026-08-10 01:13:06'),(6080,'college_news','人工智能学院','党建领航 数字赋能 青春筑梦 -现代技术...',NULL,'https://xdjsxy.mycc.edu.cn/info/1008/1644.htm','2025.05.26','2026-08-10 01:13:06'),(6081,'college_news','智能制造与工程学院','我校在第十九届“高教杯”全国大学生先进成...',NULL,'https://xdcsjsxy.mycc.edu.cn/info/1049/2864.htm',NULL,'2026-08-10 01:13:06'),(6082,'college_news','智能制造与工程学院','关于开展智能制造与工程学院院领导接待日活...',NULL,'https://xdcsjsxy.mycc.edu.cn/info/1049/2772.htm',NULL,'2026-08-10 01:13:06'),(6083,'college_news','健康与教育学院','深化国际校际交流 共绘中越育人新篇',NULL,'https://xdfw.mycc.edu.cn/info/1045/2376.htm',NULL,'2026-08-10 01:13:06'),(6084,'college_news','健康与教育学院','健康与教育学院2026届毕业典礼圆满举行',NULL,'https://xdfw.mycc.edu.cn/info/1045/2372.htm',NULL,'2026-08-10 01:13:06'),(6085,'college_news','商学院','深化产教融合 共筑育人新局——绵阳城市学院商学院与四川省金诺瑞食品有限公司开展...',NULL,'https://jgxy.mycc.edu.cn/info/1224/5214.htm',NULL,'2026-08-10 01:13:06'),(6086,'college_news','商学院','专业探秘|我校工商管理专业产教融合育人的探索与实践',NULL,'https://jgxy.mycc.edu.cn/info/1224/5222.htm',NULL,'2026-08-10 01:13:06'),(6087,'college_news','创意设计学院','艺术设计学专业《光影交互视觉设计',NULL,'https://cysjxy.mycc.edu.cn/info/1021/1792.htm','2026-07-16','2026-08-10 01:13:06'),(6088,'college_news','创意设计学院','学院与绵阳百草盛源科养殖专业合作',NULL,'https://cysjxy.mycc.edu.cn/info/1021/1791.htm','2026-07-16','2026-08-10 01:13:06'),(6089,'college_news','终身教育学院','中国教育报报道：勇立潮头担大任 砥砺深...',NULL,'https://jxjy.mycc.edu.cn/info/1011/1130.htm',NULL,'2026-08-10 01:13:06'),(6090,'college_news','终身教育学院','专业交付赋能学工队伍转型升级，全案策...',NULL,'https://jxjy.mycc.edu.cn/info/1011/1487.htm',NULL,'2026-08-10 01:13:06');
/*!40000 ALTER TABLE `campus_impression_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `campus_sceneries`
--

DROP TABLE IF EXISTS `campus_sceneries`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `campus_sceneries` (
  `id` int NOT NULL AUTO_INCREMENT,
  `title` varchar(100) NOT NULL,
  `image_url` varchar(255) NOT NULL,
  `description` text,
  `location` varchar(100) DEFAULT NULL,
  `area` varchar(20) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `campus_sceneries`
--

LOCK TABLES `campus_sceneries` WRITE;
/*!40000 ALTER TABLE `campus_sceneries` DISABLE KEYS */;
INSERT INTO `campus_sceneries` VALUES (1,'图书馆（安州）','/images/lib_anzhou.jpg','现代化学习空间','校园中心','anzhou'),(2,'教学楼群（安州）','/images/teaching_anzhou.jpg','安州主教学区','校园东侧','anzhou'),(3,'校园湖景（安州）','/images/lake_anzhou.jpg','安州休闲景区','校园西侧','anzhou'),(4,'图书馆（游仙）','/images/lib_youxian.jpg','游仙图书馆','校园中心','youxian'),(5,'教学楼群（游仙）','/images/teaching_youxian.jpg','游仙主教学区','校园东侧','youxian'),(6,'校园林荫道（游仙）','/images/tree_youxian.jpg','游仙林荫大道','主干道','youxian');
/*!40000 ALTER TABLE `campus_sceneries` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `certificates`
--

DROP TABLE IF EXISTS `certificates`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `certificates` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` int NOT NULL,
  `title` varchar(200) NOT NULL,
  `competition_name` varchar(200) DEFAULT NULL,
  `award_level` enum('SCHOOL','CITY','PROVINCE','NATIONAL','INTERNATIONAL') DEFAULT NULL,
  `date` date DEFAULT NULL,
  `description` text,
  `image_url` varchar(255) DEFAULT NULL,
  `status` enum('PENDING','APPROVED','REJECTED') NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_certificates_student_id` (`student_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `certificates`
--

LOCK TABLES `certificates` WRITE;
/*!40000 ALTER TABLE `certificates` DISABLE KEYS */;
/*!40000 ALTER TABLE `certificates` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `class_groups`
--

DROP TABLE IF EXISTS `class_groups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `class_groups` (
  `id` int NOT NULL AUTO_INCREMENT,
  `major_id` int NOT NULL,
  `name` varchar(100) NOT NULL COMMENT '班级名称，如 2024级软件工程1班',
  `grade` int NOT NULL COMMENT '入学年份',
  `student_count` int DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `major_id` (`major_id`,`grade`,`name`),
  KEY `ix_class_groups_major_id` (`major_id`),
  CONSTRAINT `class_groups_ibfk_1` FOREIGN KEY (`major_id`) REFERENCES `majors` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=23 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `class_groups`
--

LOCK TABLES `class_groups` WRITE;
/*!40000 ALTER TABLE `class_groups` DISABLE KEYS */;
INSERT INTO `class_groups` VALUES (1,2,'2024级软件工程1班',2024,NULL,'2026-07-21 02:22:00'),(2,2,'2024级软件工程2班',2024,NULL,'2026-07-21 02:22:00'),(3,1,'2024级计算机科学与技术1班',2024,NULL,'2026-07-21 02:22:00'),(4,3,'2024级电子信息工程1班',2024,NULL,'2026-07-21 02:22:00'),(5,4,'2024级通信工程1班',2024,NULL,'2026-07-21 02:22:00'),(6,5,'2024级物联网工程1班',2024,NULL,'2026-07-21 02:22:00'),(7,6,'2024级人工智能1班',2024,NULL,'2026-07-21 02:22:00'),(8,7,'2024级机械设计制造及其自动化1班',2024,NULL,'2026-07-21 02:22:00'),(9,8,'2024级电气工程及其自动化1班',2024,NULL,'2026-07-21 02:22:00'),(10,9,'2024级自动化1班',2024,NULL,'2026-07-21 02:22:00'),(11,12,'2024级土木工程1班',2024,NULL,'2026-07-21 02:22:00'),(12,13,'2024级工程造价1班',2024,NULL,'2026-07-21 02:22:00'),(13,18,'2024级产品设计1班',2024,NULL,'2026-07-21 02:22:00'),(14,23,'2024级数字媒体技术1班',2024,NULL,'2026-07-21 02:22:00'),(15,21,'2024级风景园林1班',2024,NULL,'2026-07-21 02:22:00'),(16,24,'2024级财务管理1班',2024,NULL,'2026-07-21 02:22:00'),(17,25,'2024级电子商务1班',2024,NULL,'2026-07-21 02:22:00'),(18,26,'2024级工商管理1班',2024,NULL,'2026-07-21 02:22:00'),(19,27,'2024级金融工程1班',2024,NULL,'2026-07-21 02:22:00'),(20,29,'2024级体育教育1班',2024,NULL,'2026-07-21 02:22:00'),(21,32,'2024级学前教育1班',2024,NULL,'2026-07-21 02:22:00'),(22,33,'2024级英语1班',2024,NULL,'2026-07-21 02:22:00');
/*!40000 ALTER TABLE `class_groups` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `colleges`
--

DROP TABLE IF EXISTS `colleges`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `colleges` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `code` varchar(20) NOT NULL COMMENT '学院代码，如 SE',
  `description` varchar(200) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  UNIQUE KEY `code` (`code`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `colleges`
--

LOCK TABLES `colleges` WRITE;
/*!40000 ALTER TABLE `colleges` DISABLE KEYS */;
INSERT INTO `colleges` VALUES (1,'人工智能学院','AI','安州校区，培养计算机、软件、电子信息、通信、物联网、人工智能人才','2026-07-21 02:22:00'),(2,'智能制造与工程学院','ME','安州校区，培养机械、自动化、土木、交通、测绘、电气工程人才','2026-07-21 02:22:00'),(3,'创意设计学院','CD','安州校区，培养产品设计、新媒体艺术、风景园林、城乡规划、数字媒体技术人才','2026-07-21 02:22:00'),(4,'商学院','BUS','游仙校区，培养财务管理、电子商务、工商管理、金融工程、物流工程人才','2026-07-21 02:22:00'),(5,'健康与教育学院','HE','游仙校区，培养体育教育、学前教育、健康服务与管理、英语人才','2026-07-21 02:22:00'),(6,'马克思主义学院','MARX','负责全校思想政治理论课教学','2026-07-21 02:22:00'),(7,'终身教育学院','LIFE','负责继续教育与终身学习','2026-07-21 02:22:00');
/*!40000 ALTER TABLE `colleges` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `conversation_messages`
--

DROP TABLE IF EXISTS `conversation_messages`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `conversation_messages` (
  `id` int NOT NULL AUTO_INCREMENT,
  `conversation_id` int NOT NULL,
  `role` varchar(20) NOT NULL,
  `content` text NOT NULL,
  `timestamp` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_conversation_messages_conversation_id` (`conversation_id`),
  CONSTRAINT `conversation_messages_ibfk_1` FOREIGN KEY (`conversation_id`) REFERENCES `conversations` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `conversation_messages`
--

LOCK TABLES `conversation_messages` WRITE;
/*!40000 ALTER TABLE `conversation_messages` DISABLE KEYS */;
/*!40000 ALTER TABLE `conversation_messages` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `conversation_summaries`
--

DROP TABLE IF EXISTS `conversation_summaries`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `conversation_summaries` (
  `id` int NOT NULL AUTO_INCREMENT,
  `conversation_id` int NOT NULL,
  `student_id` int NOT NULL,
  `summary` text NOT NULL,
  `key_insights` json DEFAULT NULL,
  `topics` json DEFAULT NULL,
  `sentiment` varchar(20) NOT NULL,
  `message_count` int NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_conversation_summaries_conversation_id` (`conversation_id`),
  KEY `ix_conversation_summaries_student_id` (`student_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `conversation_summaries`
--

LOCK TABLES `conversation_summaries` WRITE;
/*!40000 ALTER TABLE `conversation_summaries` DISABLE KEYS */;
/*!40000 ALTER TABLE `conversation_summaries` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `conversations`
--

DROP TABLE IF EXISTS `conversations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `conversations` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `title` varchar(200) NOT NULL,
  `type` enum('NORMAL','PROJECT') NOT NULL,
  `project_template` varchar(50) DEFAULT NULL,
  `project_stage` varchar(50) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_conversations_user_id` (`user_id`),
  CONSTRAINT `conversations_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `conversations`
--

LOCK TABLES `conversations` WRITE;
/*!40000 ALTER TABLE `conversations` DISABLE KEYS */;
/*!40000 ALTER TABLE `conversations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `courses`
--

DROP TABLE IF EXISTS `courses`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `courses` (
  `id` int NOT NULL AUTO_INCREMENT,
  `class_group_id` int NOT NULL,
  `name` varchar(100) NOT NULL,
  `teacher` varchar(50) NOT NULL,
  `location` varchar(100) NOT NULL,
  `day_of_week` int NOT NULL COMMENT '星期几 1-7',
  `start_period` int NOT NULL,
  `end_period` int NOT NULL,
  `week_start` int NOT NULL,
  `week_end` int NOT NULL,
  `semester` varchar(20) NOT NULL COMMENT '学期，如 2024-2025-1',
  `credit` float DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_courses_class_group_id` (`class_group_id`),
  KEY `ix_courses_class_semester` (`class_group_id`,`semester`),
  CONSTRAINT `courses_ibfk_1` FOREIGN KEY (`class_group_id`) REFERENCES `class_groups` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=31 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `courses`
--

LOCK TABLES `courses` WRITE;
/*!40000 ALTER TABLE `courses` DISABLE KEYS */;
INSERT INTO `courses` VALUES (1,1,'软件工程','王老师','安州教学楼301',1,1,2,1,16,'2024-2025-2',3,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(2,1,'数据结构','赵老师','安州教学楼205',1,3,4,1,8,'2024-2025-2',4,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(3,1,'操作系统','陈老师','安州教学楼302',3,1,2,9,16,'2024-2025-2',4,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(4,1,'计算机网络','刘老师','安州实验楼401',5,5,6,1,12,'2024-2025-2',3,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(5,1,'Web前端开发','张老师','安州实验楼301',4,5,6,1,10,'2024-2025-2',3,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(6,2,'软件工程','王老师','安州教学楼301',1,5,6,1,12,'2024-2025-2',3,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(7,2,'Java程序设计','张老师','安州实验楼301',4,1,2,5,16,'2024-2025-2',3,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(8,2,'离散数学','王老师','安州教学楼302',4,3,4,10,16,'2024-2025-2',3,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(9,3,'算法设计与分析','陈老师','安州教学楼301',2,5,6,1,16,'2024-2025-2',3,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(10,3,'C++程序设计','赵老师','安州实验楼401',3,1,2,1,8,'2024-2025-2',4,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(11,4,'电路分析基础','李老师','安州实验楼501',1,1,2,1,12,'2024-2025-2',4,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(12,4,'模拟电子技术','周老师','安州实验楼502',3,3,4,1,16,'2024-2025-2',3,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(13,7,'深度学习','吴老师','安州实验楼501',2,1,2,1,16,'2024-2025-2',3,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(14,7,'计算机视觉','周老师','安州实验楼502',4,3,4,9,16,'2024-2025-2',3,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(15,11,'建筑材料','黄老师','安州建工楼101',1,1,2,1,10,'2024-2025-2',3,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(16,11,'建筑制图','杨老师','安州建工楼204',3,5,6,6,16,'2024-2025-2',2,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(17,16,'基础会计','钱老师','游仙经管楼301',1,1,2,1,16,'2024-2025-2',3,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(18,16,'财务管理','孙老师','游仙经管楼302',3,3,4,1,16,'2024-2025-2',3,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(19,17,'电子商务概论','赵老师','游仙经管楼301',2,1,2,1,16,'2024-2025-2',3,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(20,17,'网络营销','孙老师','游仙经管楼302',4,3,4,9,16,'2024-2025-2',3,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(21,18,'管理学原理','赵老师','游仙经管楼301',2,1,2,1,16,'2024-2025-2',3,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(22,18,'微观经济学','孙老师','游仙经管楼302',4,3,4,1,8,'2024-2025-2',3,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(23,19,'金融学基础','钱老师','游仙经管楼303',1,3,4,1,16,'2024-2025-2',3,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(24,19,'概率论与数理统计','赵老师','游仙教学楼201',3,1,2,1,12,'2024-2025-2',4,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(25,20,'运动解剖学','林老师','游仙体育楼101',1,1,2,1,16,'2024-2025-2',3,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(26,20,'体育教学论','陈老师','游仙教学楼301',3,3,4,1,16,'2024-2025-2',3,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(27,21,'学前教育学','林老师','游仙教育楼201',2,1,2,1,16,'2024-2025-2',3,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(28,21,'儿童心理学','陈老师','游仙教育楼202',4,3,4,1,16,'2024-2025-2',3,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(29,22,'综合英语','林老师','游仙外语楼101',1,1,2,1,16,'2024-2025-2',4,'2026-07-21 02:22:04','2026-07-21 02:22:04'),(30,22,'英语听力','陈老师','游仙外语楼201',3,3,4,1,16,'2024-2025-2',2,'2026-07-21 02:22:04','2026-07-21 02:22:04');
/*!40000 ALTER TABLE `courses` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `document_chunks`
--

DROP TABLE IF EXISTS `document_chunks`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `document_chunks` (
  `id` int NOT NULL AUTO_INCREMENT,
  `document_id` int NOT NULL,
  `content` text NOT NULL,
  `chunk_index` int NOT NULL,
  `embedding_json` text,
  `created_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `document_id` (`document_id`),
  CONSTRAINT `document_chunks_ibfk_1` FOREIGN KEY (`document_id`) REFERENCES `documents` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `document_chunks`
--

LOCK TABLES `document_chunks` WRITE;
/*!40000 ALTER TABLE `document_chunks` DISABLE KEYS */;
/*!40000 ALTER TABLE `document_chunks` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `documents`
--

DROP TABLE IF EXISTS `documents`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `documents` (
  `id` int NOT NULL AUTO_INCREMENT,
  `filename` varchar(255) NOT NULL,
  `file_type` varchar(50) NOT NULL,
  `file_path` varchar(500) NOT NULL,
  `status` varchar(20) NOT NULL,
  `chunk_count` int NOT NULL,
  `uploaded_by` int DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `uploaded_by` (`uploaded_by`),
  CONSTRAINT `documents_ibfk_1` FOREIGN KEY (`uploaded_by`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `documents`
--

LOCK TABLES `documents` WRITE;
/*!40000 ALTER TABLE `documents` DISABLE KEYS */;
/*!40000 ALTER TABLE `documents` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `exams`
--

DROP TABLE IF EXISTS `exams`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `exams` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` int NOT NULL,
  `course_name` varchar(100) NOT NULL,
  `exam_date` date NOT NULL,
  `start_time` time NOT NULL,
  `end_time` time NOT NULL,
  `location` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_exams_student_id` (`student_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `exams`
--

LOCK TABLES `exams` WRITE;
/*!40000 ALTER TABLE `exams` DISABLE KEYS */;
/*!40000 ALTER TABLE `exams` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `feedbacks`
--

DROP TABLE IF EXISTS `feedbacks`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `feedbacks` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `type` enum('BUG','FEATURE','COMPLAINT','OTHER') NOT NULL,
  `title` varchar(200) NOT NULL,
  `content` text NOT NULL,
  `contact` varchar(100) DEFAULT NULL,
  `status` enum('PENDING','PROCESSING','RESOLVED','REJECTED') NOT NULL,
  `reply` text,
  `replied_by` int DEFAULT NULL,
  `replied_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `replied_by` (`replied_by`),
  KEY `ix_feedbacks_id` (`id`),
  KEY `ix_feedbacks_user_id` (`user_id`),
  KEY `ix_feedbacks_status` (`status`),
  CONSTRAINT `feedbacks_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `feedbacks_ibfk_2` FOREIGN KEY (`replied_by`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `feedbacks`
--

LOCK TABLES `feedbacks` WRITE;
/*!40000 ALTER TABLE `feedbacks` DISABLE KEYS */;
/*!40000 ALTER TABLE `feedbacks` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `grades`
--

DROP TABLE IF EXISTS `grades`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `grades` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` int NOT NULL,
  `course_name` varchar(100) NOT NULL,
  `score` float NOT NULL,
  `credit` float NOT NULL,
  `gpa` float NOT NULL,
  `semester` varchar(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_grades_student_id` (`student_id`)
) ENGINE=InnoDB AUTO_INCREMENT=52 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `grades`
--

LOCK TABLES `grades` WRITE;
/*!40000 ALTER TABLE `grades` DISABLE KEYS */;
INSERT INTO `grades` VALUES (1,9,'高等数学(上)',72,4,2.8,'2023-2024-1'),(2,9,'大学英语(1)',68,3,2.5,'2023-2024-1'),(3,9,'思修',85,2,3.5,'2023-2024-1'),(4,9,'高等数学(下)',78,4,3,'2023-2024-2'),(5,9,'大学英语(2)',75,3,2.8,'2023-2024-2'),(6,9,'C语言',82,3,3.3,'2023-2024-2'),(7,9,'线性代数',80,3,3.2,'2023-2024-2'),(8,9,'高等数学(上)',85,4,3.5,'2024-2025-1'),(9,9,'大学英语',78,3,3,'2024-2025-1'),(10,9,'程序设计基础',92,3,4,'2024-2025-1'),(11,9,'概率论',88,3,3.7,'2024-2025-2'),(12,9,'数据结构',86,4,3.6,'2024-2025-2'),(13,9,'数据库原理',90,3,3.8,'2024-2025-2'),(14,9,'Python',93,2,4,'2024-2025-2'),(15,10,'高等数学(上)',61,4,2,'2023-2024-1'),(16,10,'大学英语(1)',55,3,1.5,'2023-2024-1'),(17,10,'思修',70,2,2.5,'2023-2024-1'),(18,10,'高等数学(下)',52,4,1.3,'2023-2024-2'),(19,10,'大学英语(2)',65,3,2.2,'2023-2024-2'),(20,10,'C语言',45,3,0,'2023-2024-2'),(21,10,'软件工程',72,3,2.8,'2024-2025-1'),(22,10,'数据库原理',68,3,2.5,'2024-2025-1'),(23,10,'Web前端开发',80,3,3.2,'2024-2025-2'),(24,11,'高等数学(上)',91,4,4,'2023-2024-1'),(25,11,'大学英语(1)',88,3,3.7,'2023-2024-1'),(26,11,'思修',90,2,3.9,'2023-2024-1'),(27,11,'高等数学(下)',93,4,4,'2023-2024-2'),(28,11,'大学英语(2)',85,3,3.5,'2023-2024-2'),(29,11,'C语言',92,3,4,'2023-2024-2'),(30,11,'线性代数',90,3,3.9,'2023-2024-2'),(31,11,'大数据导论',94,3,4,'2024-2025-1'),(32,11,'Python数据分析',96,3,4,'2024-2025-1'),(33,11,'机器学习基础',91,3,4,'2024-2025-2'),(34,11,'统计学',89,3,3.8,'2024-2025-2'),(35,12,'高等数学(上)',78,4,3,'2023-2024-1'),(36,12,'离散数学',85,3,3.5,'2023-2024-1'),(37,12,'C++程序设计',82,4,3.3,'2023-2024-1'),(38,12,'算法设计',88,3,3.7,'2024-2025-1'),(39,12,'数据结构',90,4,3.9,'2024-2025-1'),(40,13,'高等数学(上)',75,4,2.8,'2023-2024-1'),(41,13,'大学英语(1)',70,3,2.5,'2023-2024-1'),(42,13,'大数据导论',65,3,2.2,'2024-2025-1'),(43,13,'统计学',58,3,1.5,'2024-2025-1'),(44,15,'微观经济学',92,3,4,'2023-2024-1'),(45,15,'管理学原理',95,3,4,'2023-2024-1'),(46,15,'会计学基础',88,3,3.7,'2023-2024-1'),(47,15,'宏观经济学',90,3,3.9,'2024-2025-1'),(48,15,'财务管理',93,3,4,'2024-2025-1'),(49,16,'现代服务管理',72,3,2.8,'2023-2024-1'),(50,16,'客户关系管理',68,3,2.5,'2023-2024-1'),(51,16,'职场礼仪',80,2,3.2,'2024-2025-1');
/*!40000 ALTER TABLE `grades` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `group_members`
--

DROP TABLE IF EXISTS `group_members`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `group_members` (
  `id` int NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `user_id` int NOT NULL,
  `role` varchar(20) NOT NULL,
  `joined_at` datetime NOT NULL,
  `last_read_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_group_members_id` (`id`),
  KEY `ix_group_members_user_id` (`user_id`),
  KEY `ix_group_members_group_id` (`group_id`),
  CONSTRAINT `group_members_ibfk_1` FOREIGN KEY (`group_id`) REFERENCES `groups` (`id`),
  CONSTRAINT `group_members_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `group_members`
--

LOCK TABLES `group_members` WRITE;
/*!40000 ALTER TABLE `group_members` DISABLE KEYS */;
INSERT INTO `group_members` VALUES (1,1,2,'owner','2026-08-08 18:01:37',NULL),(3,1,10,'member','2026-08-08 18:01:37',NULL),(4,1,11,'member','2026-08-08 18:01:37',NULL),(5,2,5,'owner','2026-08-08 18:49:58',NULL),(7,3,5,'owner','2026-08-08 18:59:54',NULL),(8,3,9,'member','2026-08-08 18:59:54',NULL);
/*!40000 ALTER TABLE `group_members` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `group_messages`
--

DROP TABLE IF EXISTS `group_messages`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `group_messages` (
  `id` int NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `sender_id` int NOT NULL,
  `content` text NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_group_messages_sender_id` (`sender_id`),
  KEY `ix_group_messages_group_id` (`group_id`),
  KEY `ix_group_messages_id` (`id`),
  CONSTRAINT `group_messages_ibfk_1` FOREIGN KEY (`group_id`) REFERENCES `groups` (`id`),
  CONSTRAINT `group_messages_ibfk_2` FOREIGN KEY (`sender_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `group_messages`
--

LOCK TABLES `group_messages` WRITE;
/*!40000 ALTER TABLE `group_messages` DISABLE KEYS */;
INSERT INTO `group_messages` VALUES (1,1,2,'hello group','2026-08-08 18:01:37'),(2,2,5,'111111','2026-08-08 19:00:21');
/*!40000 ALTER TABLE `group_messages` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `groups`
--

DROP TABLE IF EXISTS `groups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `groups` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `avatar` varchar(500) DEFAULT NULL,
  `creator_id` int NOT NULL,
  `created_at` datetime NOT NULL,
  `announcement` text,
  `is_dismissed` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `ix_groups_id` (`id`),
  KEY `ix_groups_creator_id` (`creator_id`),
  CONSTRAINT `groups_ibfk_1` FOREIGN KEY (`creator_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `groups`
--

LOCK TABLES `groups` WRITE;
/*!40000 ALTER TABLE `groups` DISABLE KEYS */;
INSERT INTO `groups` VALUES (1,'????',NULL,2,'2026-08-08 18:01:37',NULL,0),(2,'1',NULL,5,'2026-08-08 18:49:58',NULL,0),(3,'2',NULL,5,'2026-08-08 18:59:54',NULL,1);
/*!40000 ALTER TABLE `groups` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `growth_records`
--

DROP TABLE IF EXISTS `growth_records`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `growth_records` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` int NOT NULL,
  `type` enum('HONOR','COMPETITION','PRACTICE','PAPER','ACHIEVEMENT') NOT NULL,
  `title` varchar(200) NOT NULL,
  `description` text,
  `date` date NOT NULL,
  `attachment_url` varchar(255) DEFAULT NULL,
  `honor_level` varchar(20) DEFAULT NULL,
  `organizer` varchar(200) DEFAULT NULL,
  `competition_level` varchar(100) DEFAULT NULL,
  `practice_type` varchar(100) DEFAULT NULL,
  `practice_certificate` text,
  `paper_type` varchar(50) DEFAULT NULL,
  `paper_name` varchar(300) DEFAULT NULL,
  `first_author` varchar(100) DEFAULT NULL,
  `second_author` varchar(100) DEFAULT NULL,
  `third_author` varchar(100) DEFAULT NULL,
  `achievement_type` varchar(50) DEFAULT NULL,
  `achievement_name` varchar(300) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_growth_records_student_id` (`student_id`)
) ENGINE=InnoDB AUTO_INCREMENT=26 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `growth_records`
--

LOCK TABLES `growth_records` WRITE;
/*!40000 ALTER TABLE `growth_records` DISABLE KEYS */;
INSERT INTO `growth_records` VALUES (1,9,'COMPETITION','ACM校赛一等奖',NULL,'2026-01-22',NULL,NULL,'软件学院','校级',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(2,9,'HONOR','国家励志奖学金',NULL,'2026-05-22',NULL,'国家级',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(3,9,'PRACTICE','暑期企业实训',NULL,'2026-03-23',NULL,NULL,NULL,NULL,'企业实习','优秀实习生',NULL,NULL,NULL,NULL,NULL,NULL,NULL),(4,9,'ACHIEVEMENT','基于AI的考勤系统',NULL,'2026-06-21',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'软件著作权',NULL),(5,10,'PRACTICE','社区志愿服务',NULL,'2026-01-02',NULL,NULL,NULL,NULL,'志愿服务',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(6,10,'PRACTICE','迎新志愿者',NULL,'2026-04-22',NULL,NULL,NULL,NULL,'志愿服务',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(7,10,'COMPETITION','程序设计天梯赛',NULL,'2026-02-21',NULL,NULL,'计算机学院','省级',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(8,11,'PAPER','基于大数据的用户画像研究',NULL,'2026-06-06',NULL,NULL,NULL,NULL,NULL,NULL,'期刊论文','计算机应用研究','王五',NULL,NULL,NULL,NULL),(9,11,'COMPETITION','数学建模国赛省一等奖',NULL,'2026-01-02',NULL,NULL,'中国工业与应用数学学会','省级',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(10,11,'ACHIEVEMENT','数据可视化平台',NULL,'2026-04-12',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'软件著作权',NULL),(11,11,'HONOR','优秀学生标兵',NULL,'2026-06-21',NULL,'校级',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(12,12,'COMPETITION','ICPC亚洲区域赛银奖',NULL,'2025-11-13',NULL,NULL,'ACM/ICPC','亚洲区',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(13,12,'COMPETITION','蓝桥杯省一等奖',NULL,'2026-02-21',NULL,NULL,'工业和信息化部','省级',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(14,12,'HONOR','创新能力先进个人',NULL,'2026-05-22',NULL,'校级',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(15,13,'HONOR','优秀志愿者',NULL,'2025-09-24',NULL,'院级',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(16,14,'PRACTICE','新生军训优秀学员',NULL,'2026-06-21',NULL,NULL,NULL,NULL,'军训',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(17,15,'HONOR','国家奖学金',NULL,'2026-04-22',NULL,'国家级',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(18,15,'HONOR','优秀学生干部',NULL,'2026-01-22',NULL,'校级',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(19,15,'PAPER','共享经济下的大学生消费行为',NULL,'2026-05-22',NULL,NULL,NULL,NULL,NULL,NULL,'普刊论文','经济研究导刊','周九',NULL,NULL,NULL,NULL),(20,15,'COMPETITION','全国大学生市场调查大赛省一等奖',NULL,'2026-03-23',NULL,NULL,'教育部统计学教指委','省级',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(21,15,'PRACTICE','农业银行实习',NULL,'2026-01-02',NULL,NULL,NULL,NULL,'企业实习','优秀实习生',NULL,NULL,NULL,NULL,NULL,NULL,NULL),(22,9,'HONOR','教师创建的荣誉记录',NULL,'2025-01-01',NULL,'校级',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(24,9,'HONOR','教师创建的荣誉记录',NULL,'2025-01-01',NULL,'校级',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL);
/*!40000 ALTER TABLE `growth_records` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `knowledge_base`
--

DROP TABLE IF EXISTS `knowledge_base`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `knowledge_base` (
  `id` int NOT NULL AUTO_INCREMENT,
  `category` varchar(50) NOT NULL,
  `question` varchar(500) NOT NULL,
  `answer` text NOT NULL,
  `tags` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_knowledge_base_category` (`category`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `knowledge_base`
--

LOCK TABLES `knowledge_base` WRITE;
/*!40000 ALTER TABLE `knowledge_base` DISABLE KEYS */;
INSERT INTO `knowledge_base` VALUES (1,'办事流程','怎么请假','请假流程：学生可在对话框输入请假需求，我会自动生成请假申请。也可通过办事服务页面手动提交。',NULL),(2,'办事流程','如何申请在校证明','1. 登录系统 2. 进入办事服务页面 3. 选择证明申请 4. 填写信息 5. 审批通过后可在电子版下载。',NULL),(3,'办事流程','怎么查课表','对话框输入\'查课表\'或\'今天有什么课\'，我会自动调取课表信息。',NULL),(4,'办事流程','怎么查成绩','对话框输入\'查成绩\'自动调取成绩信息，也可到成绩查询页面查看。',NULL),(5,'校园导航','图书馆在哪里','安州校区位于校园中心；游仙校区位于校园中心区域。',NULL),(6,'校园导航','食堂营业时间','早餐7:00-9:00，午餐11:30-13:00，晚餐17:30-19:00。',NULL),(7,'校园导航','体育馆开放时间','周一至周五6:30-21:30，周末8:00-21:00。',NULL),(8,'规章制度','宿舍管理规定','按时归寝(23:00前)，禁止违规电器，保持卫生，不得留宿外人。',NULL),(9,'规章制度','考试纪律','提前15分钟入场，携带学生证，禁止手机，严禁作弊。',NULL),(10,'规章制度','奖学金评定标准','学年GPA排名、综合素质测评、无违纪处分。',NULL),(11,'校园生活','校园卡怎么充值','微信小程序、食堂充值窗口、自助充值机。',NULL),(12,'校园生活','心理咨询中心','行政楼3楼305室，紧急情况可联系辅导员。',NULL);
/*!40000 ALTER TABLE `knowledge_base` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `leave_requests`
--

DROP TABLE IF EXISTS `leave_requests`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `leave_requests` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` int NOT NULL,
  `start_date` date NOT NULL,
  `end_date` date NOT NULL,
  `reason` text NOT NULL,
  `leave_type` enum('COMPETITION','SICK','PERSONAL','OTHER') NOT NULL,
  `status` enum('PENDING','APPROVED','REJECTED') NOT NULL,
  `tutor_id` int DEFAULT NULL,
  `reject_reason` text,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_leave_requests_student_id` (`student_id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `leave_requests`
--

LOCK TABLES `leave_requests` WRITE;
/*!40000 ALTER TABLE `leave_requests` DISABLE KEYS */;
INSERT INTO `leave_requests` VALUES (1,9,'2026-05-22','2026-05-24','参加ACM校赛','COMPETITION','APPROVED',NULL,NULL,'2026-07-20 18:22:04','2026-07-20 18:22:04'),(2,9,'2026-07-26','2026-07-28','下周二参加ACM区域赛需要请假三天','COMPETITION','PENDING',NULL,NULL,'2026-07-20 18:22:04','2026-07-20 18:22:04'),(3,10,'2026-06-21','2026-06-23','回家办事','PERSONAL','REJECTED',NULL,'理由不充分，请补充详细信息','2026-07-20 18:22:04','2026-07-20 18:22:04'),(4,10,'2026-07-24','2026-07-24','身体不舒服想去医院检查','SICK','PENDING',NULL,NULL,'2026-07-20 18:22:04','2026-07-20 18:22:04'),(5,16,'2026-04-22','2026-04-22','家中有事','PERSONAL','APPROVED',NULL,NULL,'2026-07-20 18:22:04','2026-07-20 18:22:04'),(6,16,'2026-06-06','2026-06-06','身体不适','SICK','APPROVED',NULL,NULL,'2026-07-20 18:22:04','2026-07-20 18:22:04'),(7,16,'2026-07-11','2026-07-12','参加婚礼','PERSONAL','PENDING',NULL,NULL,'2026-07-20 18:22:04','2026-07-20 18:22:04'),(8,16,'2026-08-05','2026-08-07','外出实习面试','PERSONAL','PENDING',NULL,NULL,'2026-07-20 18:22:04','2026-07-20 18:22:04'),(9,9,'2025-06-01','2025-06-02','集成测试-请假','PERSONAL','PENDING',NULL,NULL,'2026-08-08 08:43:06','2026-08-08 08:43:06'),(10,9,'2025-07-01','2025-07-02','审批流程测试','PERSONAL','APPROVED',4,NULL,'2026-08-08 08:43:07','2026-08-08 08:43:07'),(11,9,'2025-06-01','2025-06-02','集成测试-请假','PERSONAL','PENDING',NULL,NULL,'2026-08-08 09:17:11','2026-08-08 09:17:11'),(12,9,'2025-07-01','2025-07-02','审批流程测试','PERSONAL','APPROVED',4,NULL,'2026-08-08 09:17:12','2026-08-08 09:17:12');
/*!40000 ALTER TABLE `leave_requests` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lost_found_comments`
--

DROP TABLE IF EXISTS `lost_found_comments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `lost_found_comments` (
  `id` int NOT NULL AUTO_INCREMENT,
  `item_id` int NOT NULL,
  `user_id` int NOT NULL,
  `content` text NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `ix_lost_found_comments_item_id` (`item_id`),
  CONSTRAINT `lost_found_comments_ibfk_1` FOREIGN KEY (`item_id`) REFERENCES `lost_found_items` (`id`),
  CONSTRAINT `lost_found_comments_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lost_found_comments`
--

LOCK TABLES `lost_found_comments` WRITE;
/*!40000 ALTER TABLE `lost_found_comments` DISABLE KEYS */;
/*!40000 ALTER TABLE `lost_found_comments` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lost_found_items`
--

DROP TABLE IF EXISTS `lost_found_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `lost_found_items` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `type` text NOT NULL,
  `title` varchar(100) NOT NULL,
  `description` text NOT NULL,
  `location` varchar(200) NOT NULL,
  `contact` varchar(200) NOT NULL,
  `image_url` varchar(500) DEFAULT NULL,
  `status` text NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_lost_found_items_user_id` (`user_id`),
  CONSTRAINT `lost_found_items_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lost_found_items`
--

LOCK TABLES `lost_found_items` WRITE;
/*!40000 ALTER TABLE `lost_found_items` DISABLE KEYS */;
INSERT INTO `lost_found_items` VALUES (1,9,'lost','1','1','1','1',NULL,'claimed','2026-08-08 07:05:02');
/*!40000 ALTER TABLE `lost_found_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `majors`
--

DROP TABLE IF EXISTS `majors`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `majors` (
  `id` int NOT NULL AUTO_INCREMENT,
  `college_id` int NOT NULL,
  `name` varchar(100) NOT NULL,
  `code` varchar(20) NOT NULL COMMENT '专业代码',
  `description` varchar(200) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `college_id` (`college_id`,`code`),
  KEY `ix_majors_college_id` (`college_id`),
  CONSTRAINT `majors_ibfk_1` FOREIGN KEY (`college_id`) REFERENCES `colleges` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=35 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `majors`
--

LOCK TABLES `majors` WRITE;
/*!40000 ALTER TABLE `majors` DISABLE KEYS */;
INSERT INTO `majors` VALUES (1,1,'计算机科学与技术','AI01','计算机系统与应用开发','2026-07-21 02:22:00'),(2,1,'软件工程','AI02','软件开发与工程管理','2026-07-21 02:22:00'),(3,1,'电子信息工程','AI03','电子信息系统设计与开发','2026-07-21 02:22:00'),(4,1,'通信工程','AI04','通信系统与网络工程','2026-07-21 02:22:00'),(5,1,'物联网工程','AI05','物联网系统设计与应用','2026-07-21 02:22:00'),(6,1,'人工智能','AI06','AI算法与应用（新增本科）','2026-07-21 02:22:00'),(7,2,'机械设计制造及其自动化','ME01','机械设计与制造','2026-07-21 02:22:00'),(8,2,'电气工程及其自动化','ME02','电气工程与自动化控制','2026-07-21 02:22:00'),(9,2,'自动化','ME03','自动化系统与控制','2026-07-21 02:22:00'),(10,2,'机器人工程','ME04','机器人系统设计与应用（新增本科）','2026-07-21 02:22:00'),(11,2,'智能制造工程','ME05','智能制造技术与系统','2026-07-21 02:22:00'),(12,2,'土木工程','ME06','建筑工程设计与施工','2026-07-21 02:22:00'),(13,2,'工程造价','ME07','工程造价管理','2026-07-21 02:22:00'),(14,2,'测绘工程','ME08','测绘与地理信息','2026-07-21 02:22:00'),(15,2,'交通工程','ME09','交通规划与工程','2026-07-21 02:22:00'),(16,2,'地理信息科学','ME10','地理信息系统与空间分析','2026-07-21 02:22:00'),(17,2,'能源与环境系统工程','ME11','能源与环境系统','2026-07-21 02:22:00'),(18,3,'产品设计','CD01','产品造型与交互设计','2026-07-21 02:22:00'),(19,3,'新媒体艺术','CD02','新媒体艺术与传播','2026-07-21 02:22:00'),(20,3,'艺术设计学','CD03','艺术设计理论与实践','2026-07-21 02:22:00'),(21,3,'风景园林','CD04','风景园林规划设计','2026-07-21 02:22:00'),(22,3,'城乡规划','CD05','城乡规划与设计','2026-07-21 02:22:00'),(23,3,'数字媒体技术','CD06','数字媒体技术与应用','2026-07-21 02:22:00'),(24,4,'财务管理','BUS01','财务管理与会计实务','2026-07-21 02:22:00'),(25,4,'电子商务','BUS02','电子商务运营与管理','2026-07-21 02:22:00'),(26,4,'工商管理','BUS03','企业管理与运营','2026-07-21 02:22:00'),(27,4,'金融工程','BUS04','金融工程与风险管理','2026-07-21 02:22:00'),(28,4,'物流工程','BUS05','物流系统规划与管理','2026-07-21 02:22:00'),(29,5,'体育教育','HE01','体育教学与训练','2026-07-21 02:22:00'),(30,5,'休闲体育','HE02','休闲体育服务与管理','2026-07-21 02:22:00'),(31,5,'健康服务与管理','HE03','健康管理与服务','2026-07-21 02:22:00'),(32,5,'学前教育','HE04','学前教育理论与实践','2026-07-21 02:22:00'),(33,5,'英语','HE05','英语语言文学与翻译','2026-07-21 02:22:00'),(34,5,'数学与应用数学','HE06','数学理论与应用','2026-07-21 02:22:00');
/*!40000 ALTER TABLE `majors` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `messages`
--

DROP TABLE IF EXISTS `messages`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `messages` (
  `id` int NOT NULL AUTO_INCREMENT,
  `sender_id` int NOT NULL,
  `receiver_id` int NOT NULL,
  `content` text NOT NULL,
  `read` tinyint(1) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_messages_sender_id` (`sender_id`),
  KEY `ix_messages_receiver_id` (`receiver_id`),
  KEY `ix_messages_id` (`id`),
  CONSTRAINT `messages_ibfk_1` FOREIGN KEY (`sender_id`) REFERENCES `users` (`id`),
  CONSTRAINT `messages_ibfk_2` FOREIGN KEY (`receiver_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `messages`
--

LOCK TABLES `messages` WRITE;
/*!40000 ALTER TABLE `messages` DISABLE KEYS */;
INSERT INTO `messages` VALUES (1,5,11,'111',1,'2026-08-08 17:17:30'),(2,5,11,'222',1,'2026-08-08 17:20:23'),(3,5,13,'11',0,'2026-08-08 17:20:38'),(4,5,11,'{\"type\":\"file\",\"text\":\"向武杰.docx\",\"url\":\"/uploads/向武杰_e6da5fd6.docx\"}',1,'2026-08-08 18:23:35');
/*!40000 ALTER TABLE `messages` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `notifications`
--

DROP TABLE IF EXISTS `notifications`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `notifications` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `title` varchar(200) NOT NULL,
  `content` text NOT NULL,
  `type` enum('SYSTEM','APPROVAL','LEAVE','CRISIS','ANNOUNCEMENT','MESSAGE','FEEDBACK') NOT NULL,
  `is_read` tinyint(1) NOT NULL,
  `link` varchar(500) DEFAULT NULL,
  `related_id` int DEFAULT NULL,
  `sender_id` int DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `sender_id` (`sender_id`),
  KEY `ix_notifications_is_read` (`is_read`),
  KEY `ix_notifications_id` (`id`),
  KEY `ix_notifications_user_id` (`user_id`),
  CONSTRAINT `notifications_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `notifications_ibfk_2` FOREIGN KEY (`sender_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `notifications`
--

LOCK TABLES `notifications` WRITE;
/*!40000 ALTER TABLE `notifications` DISABLE KEYS */;
/*!40000 ALTER TABLE `notifications` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `service_tickets`
--

DROP TABLE IF EXISTS `service_tickets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `service_tickets` (
  `id` int NOT NULL AUTO_INCREMENT,
  `applicant_id` int NOT NULL,
  `applicant_name` varchar(50) NOT NULL,
  `applicant_no` varchar(50) NOT NULL,
  `applicant_college` varchar(100) NOT NULL,
  `type` enum('LEAVE','CERTIFICATE','PROJECT') NOT NULL,
  `title` varchar(200) NOT NULL,
  `content` text NOT NULL,
  `attachment` varchar(255) DEFAULT NULL,
  `form_data` json DEFAULT NULL,
  `attachments` json DEFAULT NULL,
  `status` enum('PENDING','APPROVED','REJECTED') NOT NULL,
  `approver_id` int DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_service_tickets_applicant_id` (`applicant_id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `service_tickets`
--

LOCK TABLES `service_tickets` WRITE;
/*!40000 ALTER TABLE `service_tickets` DISABLE KEYS */;
INSERT INTO `service_tickets` VALUES (1,9,'张三','2024001','软件学院','CERTIFICATE','在校证明','实习求职需要在校证明',NULL,NULL,NULL,'PENDING',NULL,'2026-07-20 18:22:04','2026-07-20 18:22:04'),(2,10,'李四','2024002','软件学院','PROJECT','科研项目立项','基于机器学习的校园助手优化研究',NULL,NULL,NULL,'APPROVED',NULL,'2026-07-20 18:22:04','2026-07-20 18:22:04'),(3,10,'李四','2024002','软件学院','CERTIFICATE','成绩单申请','考研需要',NULL,NULL,NULL,'PENDING',NULL,'2026-07-20 18:22:04','2026-07-20 18:22:04'),(4,16,'吴十','2024008','现代服务学院','LEAVE','补假申请','上周五忘记请假，申请补假',NULL,NULL,NULL,'PENDING',NULL,'2026-07-20 18:22:04','2026-07-20 18:22:04');
/*!40000 ALTER TABLE `service_tickets` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `student_profile_snapshots`
--

DROP TABLE IF EXISTS `student_profile_snapshots`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `student_profile_snapshots` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` int NOT NULL,
  `snapshot_date` date NOT NULL,
  `academic_score` float NOT NULL,
  `psychological_risk` float NOT NULL,
  `engagement_score` float NOT NULL,
  `growth_score` float NOT NULL,
  `overall_risk` float NOT NULL,
  `behavioral_patterns` json DEFAULT NULL,
  `key_insights` json DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_student_profile_snapshots_snapshot_date` (`snapshot_date`),
  KEY `ix_student_profile_snapshots_student_id` (`student_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `student_profile_snapshots`
--

LOCK TABLES `student_profile_snapshots` WRITE;
/*!40000 ALTER TABLE `student_profile_snapshots` DISABLE KEYS */;
/*!40000 ALTER TABLE `student_profile_snapshots` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `student_projects`
--

DROP TABLE IF EXISTS `student_projects`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `student_projects` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` int NOT NULL,
  `project_name` varchar(200) NOT NULL,
  `start_date` date NOT NULL,
  `end_date` date DEFAULT NULL,
  `is_team` tinyint(1) NOT NULL,
  `team_members` varchar(500) DEFAULT NULL,
  `attachment_url` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_student_projects_student_id` (`student_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `student_projects`
--

LOCK TABLES `student_projects` WRITE;
/*!40000 ALTER TABLE `student_projects` DISABLE KEYS */;
/*!40000 ALTER TABLE `student_projects` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `system_settings`
--

DROP TABLE IF EXISTS `system_settings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `system_settings` (
  `id` int NOT NULL AUTO_INCREMENT,
  `key` varchar(100) NOT NULL,
  `value` text,
  `description` varchar(500) DEFAULT NULL,
  `updated_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_system_settings_key` (`key`),
  KEY `ix_system_settings_id` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_settings`
--

LOCK TABLES `system_settings` WRITE;
/*!40000 ALTER TABLE `system_settings` DISABLE KEYS */;
/*!40000 ALTER TABLE `system_settings` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `teacher_announcements`
--

DROP TABLE IF EXISTS `teacher_announcements`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `teacher_announcements` (
  `id` int NOT NULL AUTO_INCREMENT,
  `teacher_id` int NOT NULL,
  `title` varchar(200) NOT NULL,
  `content` text NOT NULL,
  `urgency` enum('NORMAL','IMPORTANT','URGENT') NOT NULL,
  `attachment_url` varchar(500) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_teacher_announcements_teacher_id` (`teacher_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `teacher_announcements`
--

LOCK TABLES `teacher_announcements` WRITE;
/*!40000 ALTER TABLE `teacher_announcements` DISABLE KEYS */;
/*!40000 ALTER TABLE `teacher_announcements` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `teacher_schedules`
--

DROP TABLE IF EXISTS `teacher_schedules`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `teacher_schedules` (
  `id` int NOT NULL AUTO_INCREMENT,
  `teacher_id` int NOT NULL,
  `date` date NOT NULL,
  `content` varchar(500) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_teacher_schedules_date` (`date`),
  KEY `ix_teacher_schedules_teacher_id` (`teacher_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `teacher_schedules`
--

LOCK TABLES `teacher_schedules` WRITE;
/*!40000 ALTER TABLE `teacher_schedules` DISABLE KEYS */;
/*!40000 ALTER TABLE `teacher_schedules` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `password_hash` varchar(128) NOT NULL,
  `name` varchar(50) NOT NULL,
  `role` enum('STUDENT','TEACHER','ADMIN') NOT NULL,
  `college` varchar(100) DEFAULT NULL,
  `avatar` varchar(255) DEFAULT NULL,
  `tutor_id` int DEFAULT NULL,
  `skills_json` json DEFAULT NULL,
  `gender` varchar(10) DEFAULT NULL,
  `political_status` varchar(20) DEFAULT NULL,
  `title` varchar(50) DEFAULT NULL,
  `hometown` varchar(100) DEFAULT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `department` varchar(100) DEFAULT NULL,
  `age` int DEFAULT NULL,
  `class_name` varchar(50) DEFAULT NULL COMMENT '班级',
  `class_group_id` int DEFAULT NULL COMMENT '关联班级',
  `password_changed` tinyint(1) NOT NULL COMMENT '是否已修改过密码',
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_users_username` (`username`),
  KEY `ix_users_class_group_id` (`class_group_id`),
  CONSTRAINT `users_ibfk_1` FOREIGN KEY (`class_group_id`) REFERENCES `class_groups` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'admin','$2b$12$8VuoNsXRow1I3IMDb.zM9eOB.HSF79cIEjoZeEIMhJ0c2PO0Z9OPC','管理员','ADMIN',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,0),(2,'t1001','$2b$12$FNhcuWWJv3mCd.3oA3g4aORgfWHr.S1Ac8.P0W/nMjSX2wqBBFWr.','王老师','TEACHER','人工智能学院',NULL,NULL,NULL,NULL,NULL,'导师',NULL,NULL,'绵阳城市学院',NULL,NULL,NULL,0),(3,'t1002','$2b$12$yhpg5KStxn4jmCORZjl0E.vpcLJ/NofC4SXa8vFv6ninlHcPQT8L2','李老师','TEACHER','人工智能学院',NULL,NULL,NULL,NULL,NULL,'导师',NULL,NULL,'绵阳城市学院',NULL,NULL,NULL,0),(4,'t1003','$2b$12$nVCOJL728BhSA0PA/pyKKeILln8zko5TEQyhFuRvrW18CP2h8x2Gy','陈慧敏','TEACHER','人工智能学院',NULL,NULL,NULL,NULL,NULL,'导师',NULL,NULL,'绵阳城市学院',NULL,NULL,NULL,0),(5,'t1004','$2b$12$MEVfb7QH1MRSZE5ZMsC54.chsUaQNtd3xv1Wl5a9GZBvRlSYe5jRm','张伟明','TEACHER','智能制造与工程学院',NULL,NULL,NULL,NULL,NULL,'导师',NULL,NULL,'绵阳城市学院',NULL,NULL,NULL,0),(6,'t1005','$2b$12$jag8NqnDKHH22ECHbrhtPerP3xTY0wAaci9/6.3uqP.yAMxuBHDw.','刘雅婷','TEACHER','智能制造与工程学院',NULL,NULL,NULL,NULL,NULL,'导师',NULL,NULL,'绵阳城市学院',NULL,NULL,NULL,0),(7,'t1006','$2b$12$82tMl3KP8TP5oYeen4T2j.Jf5xrgBt342NGxES/6gQ7EYD0per..K','赵志强','TEACHER','商学院',NULL,NULL,NULL,NULL,NULL,'导师',NULL,NULL,'绵阳城市学院',NULL,NULL,NULL,0),(8,'t1007','$2b$12$46D0TJB.DSl8JGsW0uztteXzQKi5in3SeyIRHs9h.23RYG.TfqwKC','林晓娟','TEACHER','健康与教育学院',NULL,NULL,NULL,NULL,NULL,'导师',NULL,NULL,'绵阳城市学院',NULL,NULL,NULL,0),(9,'2024001','$2b$12$wV3h7OTXuIZfPEcGmjTbC.4l9AxOcU0Sp1ZITMxAoSdrTLf0Vyxya','张三','STUDENT','人工智能学院',NULL,4,'{\"skills\": [{\"name\": \"Python\", \"context\": \"\"}, {\"name\": \"Vue\", \"context\": \"\"}], \"interests\": [\"编程\"]}',NULL,NULL,NULL,NULL,NULL,NULL,21,'2024级软件工程1班',1,0),(10,'2024002','$2b$12$3jqxBz18RGix/58jiKvO1e5efbqLhDQZrkdihxbnv/wVPZSabhPrW','李四','STUDENT','人工智能学院',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2024级软件工程1班',1,0),(11,'2024003','$2b$12$nJvtACYjq6PWCLnFESFi2.tWnWVrsUXX3Fu//GwGUg4bS07DRFYdS','王五','STUDENT','人工智能学院',NULL,5,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2024级计算机科学与技术1班',3,0),(12,'2024004','$2b$12$xz/FFdjWqbXu1UKRaxwcCuSOgT7TOmhgNR5.DX4boEENiMUsWq.Xy','赵六','STUDENT','人工智能学院',NULL,4,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2024级软件工程2班',2,0),(13,'2024005','$2b$12$aHmDOcVZIvKe0c9tiJ39Tez5mpjJ0TXzyBGOfExrIrgONKnS7G90G','钱七','STUDENT','人工智能学院',NULL,5,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2024级电子信息工程1班',4,0),(14,'2024006','$2b$12$UKKuqMyQZ7uAzPLVwZ1CO.7HrtE6cijG2NeqButGsFAiVxO12mjRG','孙八','STUDENT','智能制造与工程学院',NULL,6,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2024级土木工程1班',11,0),(15,'2024007','$2b$12$YglzZ4qbJkiZ9yGm.Jaf9.wUqbUqajGSPF27XIrfec736JddbeIey','周九','STUDENT','商学院',NULL,7,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2024级财务管理1班',16,0),(16,'2024008','$2b$12$3wFQOOEKFnHFhK7ud/rKKuz9mm4qtgnOd2mvmq1NzzLRlv0Bmvu3K','吴十','STUDENT','健康与教育学院',NULL,8,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2024级体育教育1班',20,0),(17,'2024009','$2b$12$6DWDvLwYJuD51wrt.GfQVORhreZq2f3bmFOjWVNjVkgKRciWjkviS','郑十一','STUDENT','商学院',NULL,4,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2024级电子商务1班',17,0);
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping events for database 'smart_campus'
--

--
-- Dumping routines for database 'smart_campus'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-08-10  1:32:59
