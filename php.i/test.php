<?php
date_default_timezone_set("Asia/Kolkata");

echo "<h2>PHP is working ✅</h2>";
echo "<p>Date/Time: " . date("Y-m-d H:i:s") . "</p>";
echo "<p>PHP Version: " . phpversion() . "</p>";
echo "<p>Server: " . ($_SERVER['SERVER_SOFTWARE'] ?? 'unknown') . "</p>";

echo "<hr>";
echo "<h3>phpinfo()</h3>";
phpinfo();
