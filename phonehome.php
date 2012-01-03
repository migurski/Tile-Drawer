<?php

    $headers = getallheaders();
    $stated_length = $headers['Content-Length'];
    $call_filename = sprintf('%s/calls/%s-%s.txt', dirname(__FILE__), $_SERVER['REMOTE_ADDR'], uniqid());
    
    $call = @fopen($call_filename, 'w');
    $stdin = @fopen('php://input', 'r');
    
    if(is_numeric($stated_length) && $call && $stdin)
    {
        fwrite($call, fread($stdin, intval($stated_length)));
        fclose($call);
        chmod($call_filename, 0666);
        
        header('HTTP/1.1 201');
        die("OK\n");
    }
    
    header('HTTP/1.1 500');
    die("*thunk*\n");

?>