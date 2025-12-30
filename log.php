<?php
$logFile = __DIR__ . '/stderr.log';

if (file_exists($logFile)) {
    echo "<h2>stderr.log Contents</h2>";
    echo "<pre>";
    echo htmlspecialchars(file_get_contents($logFile));
    echo "</pre>";
} else {
    echo "stderr.log file not found in the current directory.";
}
?>