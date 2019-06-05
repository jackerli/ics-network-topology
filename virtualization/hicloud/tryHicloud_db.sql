-- MySQL dump 10.13  Distrib 5.5.49, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: hicloud_db
-- ------------------------------------------------------
-- Server version	5.5.49-0+deb7u1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `ip_pools`
--

DROP TABLE IF EXISTS `ip_pools`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ip_pools` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `uuid` varchar(255) DEFAULT NULL,
  `name` varchar(255) DEFAULT NULL,
  `datacenter_id` int(11) DEFAULT NULL,
  `netmask` varchar(255) DEFAULT NULL,
  `gateway` varchar(255) DEFAULT NULL,
  `ip_start` varchar(255) DEFAULT NULL,
  `ip_end` varchar(255) DEFAULT NULL,
  `ip_type` varchar(255) DEFAULT NULL,
  `dns` varchar(255) DEFAULT NULL,
  `current_ip` varchar(255) DEFAULT NULL,
  `out_of_usage` int(11) DEFAULT NULL,
  `reserved` varchar(255) DEFAULT NULL,
  `vlan` int(11) DEFAULT NULL,
  `ips_count` int(11) DEFAULT '0',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ip_pools`
--

LOCK TABLES `ip_pools` WRITE;
/*!40000 ALTER TABLE `ip_pools` DISABLE KEYS */;
INSERT INTO `ip_pools` VALUES (2,'22beb50c-2af0-11e6-9477-000c29bf8d39','192.168.60.100-192.168.60.200',1,'255.255.255.0','192.168.60.1','192.168.60.100','192.168.60.200','ipv4','1.2.4.8',NULL,NULL,NULL,1,101);
/*!40000 ALTER TABLE `ip_pools` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `ips`
--

DROP TABLE IF EXISTS `ips`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ips` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `uuid` varchar(48) DEFAULT NULL,
  `ip` text,
  `ip_pool_id` int(11) DEFAULT NULL,
  `status` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=123 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ips`
--

LOCK TABLES `ips` WRITE;
/*!40000 ALTER TABLE `ips` DISABLE KEYS */;
INSERT INTO `ips` VALUES (22,'22bf6c90-2af0-11e6-9477-000c29bf8d39','192.168.60.100',2,1),(36,'22c5a57e-2af0-11e6-9477-000c29bf8d39','192.168.60.114',2,1),(37,'22c5fdee-2af0-11e6-9477-000c29bf8d39','192.168.60.115',2,1),(38,'22c6358e-2af0-11e6-9477-000c29bf8d39','192.168.60.116',2,0),(39,'22c68d0e-2af0-11e6-9477-000c29bf8d39','192.168.60.117',2,0),(40,'22c6c0c6-2af0-11e6-9477-000c29bf8d39','192.168.60.118',2,0),(41,'22c72020-2af0-11e6-9477-000c29bf8d39','192.168.60.119',2,0),(42,'22c7568a-2af0-11e6-9477-000c29bf8d39','192.168.60.120',2,0),(43,'22c7b058-2af0-11e6-9477-000c29bf8d39','192.168.60.121',2,0),(44,'22c7e852-2af0-11e6-9477-000c29bf8d39','192.168.60.122',2,0),(45,'22c81a34-2af0-11e6-9477-000c29bf8d39','192.168.60.123',2,0),(46,'22c8704c-2af0-11e6-9477-000c29bf8d39','192.168.60.124',2,0),(47,'22c8b386-2af0-11e6-9477-000c29bf8d39','192.168.60.125',2,0),(48,'22c90804-2af0-11e6-9477-000c29bf8d39','192.168.60.126',2,0),(49,'22c93d38-2af0-11e6-9477-000c29bf8d39','192.168.60.127',2,0),(50,'22c99670-2af0-11e6-9477-000c29bf8d39','192.168.60.128',2,0),(51,'22c9ca3c-2af0-11e6-9477-000c29bf8d39','192.168.60.129',2,0),(52,'22ca3ec2-2af0-11e6-9477-000c29bf8d39','192.168.60.130',2,0),(53,'22ca8256-2af0-11e6-9477-000c29bf8d39','192.168.60.131',2,0),(54,'22cb2c06-2af0-11e6-9477-000c29bf8d39','192.168.60.132',2,0),(55,'22cbc968-2af0-11e6-9477-000c29bf8d39','192.168.60.133',2,0),(56,'22cc8808-2af0-11e6-9477-000c29bf8d39','192.168.60.134',2,0),(57,'22cd065c-2af0-11e6-9477-000c29bf8d39','192.168.60.135',2,0),(58,'22cd8654-2af0-11e6-9477-000c29bf8d39','192.168.60.136',2,0),(59,'22ce14f2-2af0-11e6-9477-000c29bf8d39','192.168.60.137',2,0),(60,'22ceacdc-2af0-11e6-9477-000c29bf8d39','192.168.60.138',2,0),(61,'22cf55ce-2af0-11e6-9477-000c29bf8d39','192.168.60.139',2,0),(62,'22cfd184-2af0-11e6-9477-000c29bf8d39','192.168.60.140',2,0),(63,'22d08d18-2af0-11e6-9477-000c29bf8d39','192.168.60.141',2,0),(64,'22d0e7cc-2af0-11e6-9477-000c29bf8d39','192.168.60.142',2,0),(65,'22d122c8-2af0-11e6-9477-000c29bf8d39','192.168.60.143',2,0),(66,'22d1b1a2-2af0-11e6-9477-000c29bf8d39','192.168.60.144',2,0),(67,'22d20f12-2af0-11e6-9477-000c29bf8d39','192.168.60.145',2,0),(68,'22d244be-2af0-11e6-9477-000c29bf8d39','192.168.60.146',2,0),(69,'22d27af6-2af0-11e6-9477-000c29bf8d39','192.168.60.147',2,0),(70,'22d2fd00-2af0-11e6-9477-000c29bf8d39','192.168.60.148',2,0),(71,'22d371fe-2af0-11e6-9477-000c29bf8d39','192.168.60.149',2,0),(72,'22d3a980-2af0-11e6-9477-000c29bf8d39','192.168.60.150',2,0),(73,'22d4399a-2af0-11e6-9477-000c29bf8d39','192.168.60.151',2,0),(74,'22d497e6-2af0-11e6-9477-000c29bf8d39','192.168.60.152',2,0),(75,'22d4cc8e-2af0-11e6-9477-000c29bf8d39','192.168.60.153',2,0),(76,'22d53fc0-2af0-11e6-9477-000c29bf8d39','192.168.60.154',2,0),(77,'22d5ce54-2af0-11e6-9477-000c29bf8d39','192.168.60.155',2,0),(78,'22d64bf4-2af0-11e6-9477-000c29bf8d39','192.168.60.156',2,0),(79,'22d6ef64-2af0-11e6-9477-000c29bf8d39','192.168.60.157',2,0),(80,'22d773ee-2af0-11e6-9477-000c29bf8d39','192.168.60.158',2,0),(81,'22d82618-2af0-11e6-9477-000c29bf8d39','192.168.60.159',2,0),(82,'22d8bcea-2af0-11e6-9477-000c29bf8d39','192.168.60.160',2,0),(83,'22d95f88-2af0-11e6-9477-000c29bf8d39','192.168.60.161',2,0),(84,'22d9d21a-2af0-11e6-9477-000c29bf8d39','192.168.60.162',2,0),(85,'22da27ce-2af0-11e6-9477-000c29bf8d39','192.168.60.163',2,0),(86,'22da7706-2af0-11e6-9477-000c29bf8d39','192.168.60.164',2,0),(87,'22dacabc-2af0-11e6-9477-000c29bf8d39','192.168.60.165',2,0),(88,'22dafc9e-2af0-11e6-9477-000c29bf8d39','192.168.60.166',2,0),(89,'22db81be-2af0-11e6-9477-000c29bf8d39','192.168.60.167',2,0),(90,'22dbe9a6-2af0-11e6-9477-000c29bf8d39','192.168.60.168',2,0),(91,'22dc3be0-2af0-11e6-9477-000c29bf8d39','192.168.60.169',2,0),(92,'22dc9a04-2af0-11e6-9477-000c29bf8d39','192.168.60.170',2,0),(93,'22dcd1c2-2af0-11e6-9477-000c29bf8d39','192.168.60.171',2,0),(94,'22dd2ce4-2af0-11e6-9477-000c29bf8d39','192.168.60.172',2,0),(95,'22dd7f96-2af0-11e6-9477-000c29bf8d39','192.168.60.173',2,0),(96,'22dddfea-2af0-11e6-9477-000c29bf8d39','192.168.60.174',2,0),(97,'22de1802-2af0-11e6-9477-000c29bf8d39','192.168.60.175',2,0),(98,'22de766c-2af0-11e6-9477-000c29bf8d39','192.168.60.176',2,0),(99,'22dec338-2af0-11e6-9477-000c29bf8d39','192.168.60.177',2,0),(100,'22df4060-2af0-11e6-9477-000c29bf8d39','192.168.60.178',2,0),(101,'22dfddea-2af0-11e6-9477-000c29bf8d39','192.168.60.179',2,0),(102,'22e0610c-2af0-11e6-9477-000c29bf8d39','192.168.60.180',2,0),(103,'22e11e76-2af0-11e6-9477-000c29bf8d39','192.168.60.181',2,0),(104,'22e19fea-2af0-11e6-9477-000c29bf8d39','192.168.60.182',2,0),(105,'22e24a08-2af0-11e6-9477-000c29bf8d39','192.168.60.183',2,0),(106,'22e2d2ca-2af0-11e6-9477-000c29bf8d39','192.168.60.184',2,0),(107,'22e456c2-2af0-11e6-9477-000c29bf8d39','192.168.60.185',2,0),(108,'22e4f21c-2af0-11e6-9477-000c29bf8d39','192.168.60.186',2,0),(109,'22e546f4-2af0-11e6-9477-000c29bf8d39','192.168.60.187',2,0),(110,'22e5a1bc-2af0-11e6-9477-000c29bf8d39','192.168.60.188',2,0),(111,'22e5d3a8-2af0-11e6-9477-000c29bf8d39','192.168.60.189',2,0),(112,'22e601de-2af0-11e6-9477-000c29bf8d39','192.168.60.190',2,0),(113,'22e6a0bc-2af0-11e6-9477-000c29bf8d39','192.168.60.191',2,0),(114,'22e73a90-2af0-11e6-9477-000c29bf8d39','192.168.60.192',2,0),(115,'22e7910c-2af0-11e6-9477-000c29bf8d39','192.168.60.193',2,0),(116,'22e7c1cc-2af0-11e6-9477-000c29bf8d39','192.168.60.194',2,0),(117,'22e81e9c-2af0-11e6-9477-000c29bf8d39','192.168.60.195',2,0),(118,'22e88094-2af0-11e6-9477-000c29bf8d39','192.168.60.196',2,0),(119,'22e8f650-2af0-11e6-9477-000c29bf8d39','192.168.60.197',2,0),(120,'22e980fc-2af0-11e6-9477-000c29bf8d39','192.168.60.198',2,0),(121,'22e9fca8-2af0-11e6-9477-000c29bf8d39','192.168.60.199',2,0),(122,'22ea4460-2af0-11e6-9477-000c29bf8d39','192.168.60.200',2,0);
/*!40000 ALTER TABLE `ips` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `isos`
--

DROP TABLE IF EXISTS `isos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `isos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `iso_name` varchar(255) DEFAULT NULL,
  `os_type` varchar(255) DEFAULT NULL,
  `os_version` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=9 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `isos`
--

LOCK TABLES `isos` WRITE;
/*!40000 ALTER TABLE `isos` DISABLE KEYS */;
INSERT INTO `isos` VALUES (8,'xp_x86.iso','windows','xp'),(7,'ubuntu-14.04.2-server-amd64.iso','linux','ubuntu');
/*!40000 ALTER TABLE `isos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `jobs`
--

DROP TABLE IF EXISTS `jobs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `jobs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `uuid` varchar(255) DEFAULT NULL,
  `user_id` int(11) DEFAULT NULL,
  `title` varchar(255) DEFAULT NULL,
  `description` varchar(255) DEFAULT NULL,
  `job_type` varchar(255) DEFAULT NULL,
  `content` text,
  `status` varchar(255) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `ref_obj_name` varchar(255) DEFAULT NULL,
  `ref_obj_id` int(11) DEFAULT NULL,
  `ref_obj_type` int(11) DEFAULT NULL,
  `owner_id` int(11) DEFAULT NULL,
  `group_id` int(11) DEFAULT NULL,
  `job_info` text,
  `datacenter_id` int(11) DEFAULT NULL,
  `cluster_id` int(11) DEFAULT NULL,
  `host_id` int(11) DEFAULT NULL,
  `vm_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=286 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;



--
-- Table structure for table `nics`
--

DROP TABLE IF EXISTS `nics`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `nics` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `address` varchar(255) DEFAULT NULL,
  `netmask` varchar(255) DEFAULT NULL,
  `vswitch_id` int(11) DEFAULT NULL,
  `virtual_machine_instance_id` int(11) DEFAULT NULL,
  `gateway` varchar(255) DEFAULT NULL,
  `name` varchar(255) DEFAULT NULL,
  `vlan` varchar(255) DEFAULT NULL,
  `reserved` text,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `nics`
--

LOCK TABLES `nics` WRITE;
/*!40000 ALTER TABLE `nics` DISABLE KEYS */;
/*!40000 ALTER TABLE `nics` ENABLE KEYS */;
UNLOCK TABLES;


--
-- Table structure for table `sessions`
--

DROP TABLE IF EXISTS `sessions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sessions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `session_id` varchar(255) DEFAULT NULL,
  `data` text,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=224 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;



--
-- Table structure for table `storages`
--

DROP TABLE IF EXISTS `storages`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `storages` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `uuid` varchar(255) DEFAULT NULL,
  `total_storage` varchar(255) DEFAULT NULL,
  `used_storage` varchar(255) DEFAULT NULL,
  `storage_type` varchar(255) DEFAULT NULL,
  `storage_path` varchar(255) DEFAULT NULL,
  `ip_address` varchar(255) DEFAULT NULL,
  `name` varchar(255) DEFAULT NULL,
  `user_name` varchar(255) DEFAULT NULL,
  `password` varchar(255) DEFAULT NULL,
  `status` varchar(255) DEFAULT 'new',
  `is_iso_storage` tinyint(1) DEFAULT '0',
  `origin_ip_address` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `storages`
--

LOCK TABLES `storages` WRITE;
/*!40000 ALTER TABLE `storages` DISABLE KEYS */;
INSERT INTO `storages` VALUES (1,'6498635e-2638-11e6-9477-000c29bf8d39','30013492','9979408','nfs','/var/lib/ivic/vstore','192.168.50.129','192.168.50.129','root','123456','online',1,NULL);
/*!40000 ALTER TABLE `storages` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `tasks`
--

DROP TABLE IF EXISTS `tasks`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `tasks` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `uuid` varchar(255) DEFAULT NULL,
  `job_id` int(11) DEFAULT NULL,
  `title` varchar(255) DEFAULT NULL,
  `description` varchar(255) DEFAULT NULL,
  `task_type` varchar(255) DEFAULT NULL,
  `content` text,
  `status` varchar(255) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `depend_task_id` int(11) DEFAULT NULL,
  `task_info` text,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=244 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;



--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `email` varchar(255) DEFAULT NULL,
  `password` varchar(255) DEFAULT NULL,
  `cert_id` int(11) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `active_code` varchar(255) DEFAULT NULL,
  `is_activated` tinyint(1) DEFAULT NULL,
  `lognum` int(11) DEFAULT NULL,
  `group_id` int(11) DEFAULT NULL,
  `reserved` text,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'Administrator','7c4a8d09ca3762af61e59520943dc26494f8941b',2,'2016-04-19 14:38:16','2016-04-19 14:38:16','122221222312344353236668768978976867575464356453',1,NULL,1,NULL),(2,'vmc_register','69c5fcebaa65b560eaf06c3fbeb481ae44b8d618',1,'2016-04-20 04:17:47','2016-04-20 04:17:48','097fc9293e682912d01f4fb27cb772f4c66a5704',1,0,NULL,NULL);
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;




--
-- Table structure for table `virtual_machine_containers`
--

DROP TABLE IF EXISTS `virtual_machine_containers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `virtual_machine_containers` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `hostname` varchar(255) DEFAULT NULL,
  `uuid` varchar(255) DEFAULT NULL,
  `address` varchar(255) DEFAULT NULL,
  `port` int(11) DEFAULT NULL,
  `status` varchar(255) DEFAULT NULL,
  `owner_id` int(11) DEFAULT NULL,
  `group_id` int(11) DEFAULT NULL,
  `cluster_id` int(11) DEFAULT NULL,
  `running_time` int(11) DEFAULT NULL,
  `cpu_type` varchar(255) DEFAULT NULL,
  `cpu_num` varchar(255) DEFAULT NULL,
  `cpu_usage` varchar(255) DEFAULT NULL,
  `mem_total` varchar(255) DEFAULT NULL,
  `mem_free` varchar(255) DEFAULT NULL,
  `disk_device` varchar(255) DEFAULT NULL,
  `disk_total` varchar(255) DEFAULT NULL,
  `disk_free` varchar(255) DEFAULT NULL,
  `nics_num` int(11) DEFAULT NULL,
  `net_ifname` varchar(255) DEFAULT NULL,
  `net_tx` varchar(255) DEFAULT NULL,
  `net_rx` varchar(255) DEFAULT NULL,
  `vm_name` varchar(255) DEFAULT NULL,
  `vm_state` varchar(255) DEFAULT NULL,
  `vcpu_usage` varchar(255) DEFAULT NULL,
  `vmem_total` varchar(255) DEFAULT NULL,
  `vmem_free` varchar(255) DEFAULT NULL,
  `vdisk_read` varchar(255) DEFAULT NULL,
  `vdisk_write` varchar(255) DEFAULT NULL,
  `vif_tx` varchar(255) DEFAULT NULL,
  `vif_rx` varchar(255) DEFAULT NULL,
  `metadata` varchar(255) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `vm_uuid` text,
  `capability` varchar(255) DEFAULT NULL,
  `vdisk_names` varchar(255) DEFAULT NULL,
  `vif_names` varchar(255) DEFAULT NULL,
  `all_pair_ping` text,
  `vnc_port` varchar(255) DEFAULT NULL,
  `vm_cnt` int(11) DEFAULT '0',
  `respool_cnt` int(11) DEFAULT '0',
  `reserved` varchar(255) DEFAULT NULL,
  `host_desc` varchar(255) DEFAULT NULL,
  `host_vendor_name` varchar(255) DEFAULT NULL,
  `host_type` varchar(255) DEFAULT NULL,
  `oper_system_vendor_name` varchar(255) DEFAULT NULL,
  `oper_system_name` varchar(255) DEFAULT NULL,
  `uuid_bios` varchar(255) DEFAULT NULL,
  `dns` varchar(255) DEFAULT NULL,
  `cpu_core_num` varchar(255) DEFAULT NULL,
  `cpu_thread_num` varchar(255) DEFAULT NULL,
  `diskarray_num` varchar(255) DEFAULT NULL,
  `datacenter_id` int(11) DEFAULT NULL,
  `user_name` varchar(255) DEFAULT NULL,
  `password` varchar(255) DEFAULT NULL,
  `status_flag` int(1) DEFAULT NULL,
  `hardware_id` varchar(16) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `host_name` (`hostname`),
  KEY `address` (`address`),
  KEY `owner_id` (`owner_id`),
  KEY `group_id` (`group_id`),
  KEY `cluster_id` (`cluster_id`),
  KEY `datacenter_id` (`datacenter_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;


--
-- Table structure for table `virtual_machine_instances`
--

DROP TABLE IF EXISTS `virtual_machine_instances`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `virtual_machine_instances` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `uuid` varchar(255) DEFAULT NULL,
  `hostname` varchar(255) DEFAULT NULL,
  `virtual_machine_container_id` int(11) DEFAULT NULL,
  `status` varchar(255) DEFAULT NULL,
  `virtual_cluster_instance_id` int(11) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `cpu_usage` varchar(255) DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `settings` text,
  `target_vmc_id` int(11) DEFAULT NULL,
  `mig_info` varchar(255) DEFAULT NULL,
  `runtime1` int(11) DEFAULT NULL,
  `runtime2` int(11) DEFAULT NULL,
  `vdisk_names` varchar(255) DEFAULT NULL,
  `vif_names` varchar(255) DEFAULT NULL,
  `node_index` int(11) DEFAULT NULL,
  `job_id` int(11) DEFAULT NULL,
  `capture_nics` varchar(255) DEFAULT NULL,
  `capture_expr` varchar(255) DEFAULT NULL,
  `capabilities` varchar(255) DEFAULT NULL,
  `mem_total` varchar(255) DEFAULT NULL,
  `mem_free` varchar(255) DEFAULT NULL,
  `cpu_cnt` int(11) DEFAULT NULL,
  `memory_keep_capacity` int(11) DEFAULT NULL,
  `cpu_total_capacity` int(11) DEFAULT NULL,
  `net_adapter_num` int(11) DEFAULT NULL,
  `disk_total` varchar(255) DEFAULT NULL,
  `disk_free` varchar(255) DEFAULT NULL,
  `disk_read` varchar(255) DEFAULT NULL,
  `disk_write` varchar(255) DEFAULT NULL,
  `enable_snapshot` varchar(255) DEFAULT NULL,
  `power_state` varchar(255) DEFAULT NULL,
  `temp_file_name` varchar(255) DEFAULT NULL,
  `temp_file_path` varchar(255) DEFAULT NULL,
  `storeid` varchar(255) DEFAULT NULL,
  `store_name` varchar(255) DEFAULT NULL,
  `store_type` varchar(255) DEFAULT NULL,
  `vhost_name` varchar(255) DEFAULT NULL,
  `vhost_desc` varchar(255) DEFAULT NULL,
  `file_name` varchar(255) DEFAULT NULL,
  `uuid_bios` varchar(255) DEFAULT NULL,
  `oper_system_vendor_name` varchar(255) DEFAULT NULL,
  `oper_system_name` varchar(255) DEFAULT NULL,
  `ip` text,
  `network_ids` text,
  `vif_tx` varchar(255) DEFAULT NULL,
  `vif_rx` varchar(255) DEFAULT NULL,
  `vnc_port` varchar(255) DEFAULT NULL,
  `vm_temp_id` int(11) DEFAULT NULL,
  `respool_id` int(11) DEFAULT NULL,
  `cluster_id` int(11) DEFAULT NULL,
  `dns` varchar(255) DEFAULT NULL,
  `nic_cnt` int(11) DEFAULT NULL,
  `description` text,
  `owner_id` int(11) DEFAULT NULL,
  `group_id` int(11) DEFAULT NULL,
  `current_snapshot` int(11) DEFAULT NULL,
  `snapshot_id` int(11) DEFAULT NULL,
  `reserved` varchar(255) DEFAULT NULL,
  `storage_id` int(11) DEFAULT NULL,
  `datacenter_id` int(11) DEFAULT NULL,
  `storage_type` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `hostname` (`hostname`),
  KEY `virtual_machine_container_id` (`virtual_machine_container_id`),
  KEY `vm_temp_id` (`vm_temp_id`),
  KEY `cluster_id` (`cluster_id`),
  KEY `owner_id` (`owner_id`),
  KEY `job_id` (`job_id`)
) ENGINE=InnoDB AUTO_INCREMENT=54 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `virtual_machine_instances`
--

LOCK TABLES `virtual_machine_instances` WRITE;
/*!40000 ALTER TABLE `virtual_machine_instances` DISABLE KEYS */;
INSERT INTO `virtual_machine_instances` VALUES (13,'107b03a6-5d99-11e6-9477-000c29bf8d39','0810-test1',1,'stopped',1,'2016-08-08 18:50:15','0.0','2016-08-10 22:18:05','<vNode><Uuid>107b03a6-5d99-11e6-9477-000c29bf8d39</Uuid><Type> </Type><Hostname>0810-test1</Hostname><Desc> </Desc><CpuCnt>1</CpuCnt><Mem>256</Mem><NicCnt>1</NicCnt><DiskSize>1</DiskSize><VstoreIp>127.0.0.1</VstoreIp><VstorePath>/var/lib/ivic/vstore</VstorePath><StorageType>local</StorageType><OsType>Windows</OsType><OsVersion>7</OsVersion><vTemplateRef> </vTemplateRef><IsoPath>/var/lib/ivic/vmc/nfsmount/192.168.50.129/iso/windows7.iso</IsoPath><NIC id=\'1\'><Vlan>2</Vlan><Address>192.168.60.101</Address><Netmask>255.255.255.0</Netmask><Gateway>192.168.60.1</Gateway><MAC>31:19:83:58:12:31</MAC><DNS>1.2.4.8</DNS></NIC><Password> </Password></vNode>',1,'',NULL,NULL,'NA','NA',NULL,NULL,'','','','256','0',1,NULL,NULL,NULL,'10','0','NA','NA','','','','','Iso','192.168.50.129','/var/lib/ivic/vmc/nfsmount/192.168.50.129/iso/windows7.iso','','','','','','7','192.168.60.101;','','NA','NA','-1',NULL,NULL,1,'',1,'',1,NULL,NULL,NULL,'NANA',99999,1,'local');
/*!40000 ALTER TABLE `virtual_machine_instances` ENABLE KEYS */;
UNLOCK TABLES;



--
-- Table structure for table `vswitches`
--

DROP TABLE IF EXISTS `vswitches`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `vswitches` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `uuid` varchar(255) DEFAULT NULL,
  `status` varchar(255) DEFAULT NULL,
  `virtual_machine_container_id` int(11) DEFAULT NULL,
  `virtual_cluster_instance_id` int(11) DEFAULT NULL,
  `vlab_instance_id` int(11) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `config_id` int(11) DEFAULT NULL,
  `connect_type` varchar(255) DEFAULT NULL,
  `ip` varchar(255) DEFAULT NULL,
  `internet_access` tinyint(1) DEFAULT NULL,
  `netmask` varchar(255) DEFAULT NULL,
  `gateway_virtual_machine_container_id` int(11) DEFAULT NULL,
  `port` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `vswitches`
--

LOCK TABLES `vswitches` WRITE;
/*!40000 ALTER TABLE `vswitches` DISABLE KEYS */;
/*!40000 ALTER TABLE `vswitches` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2016-08-11  8:38:31
