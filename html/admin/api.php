<?php
setlocale(LC_CTYPE, "en_US.UTF-8");
header('Content-Type: application/json; charset=UTF8');
define("_CMD", "sudo /usr/local/connectbox/bin/ConnectBoxManage.sh");
$method = $_SERVER['REQUEST_METHOD'];
$path_info = explode('/', trim($_SERVER['PATH_INFO'],'/'));
$raw_body = file_get_contents('php://input');
$json_body = json_decode($raw_body, true);

if ( count( $path_info ) < 1 ) {
    http_response_code(404);
    die('NOT FOUND');
}

$property = $path_info[0];

$valid_properties = array("ssid", "channel", "hostname", "staticsite", "password", "system", "ui-config");
if ( in_array($property, $valid_properties) ) {
    if ($method == 'GET') {
        exec(sprintf('%s get %s', _CMD, $property), $return_text, $result_int);
    } elseif ($method == 'PUT') {
        if ($property == 'ui-config') {
            exec(sprintf('%s set %s %s', _CMD, $property, escapeshellarg($raw_body)), $return_text, $result_int);
        } elseif (array_key_exists('value', $json_body) && is_string($json_body['value'])) {
            exec(sprintf('%s set %s \'%s\'', _CMD, $property, escapeshellcmd($json_body['value'])), $return_text, $result_int);
        } else {
            http_response_code(400);
            die('BAD REQUEST');
        }
    } else if ($method == 'POST') {
        if ($property == 'system') {
            if ( array_key_exists('value', $json_body) && is_string($json_body['value'])) {
                if ( $json_body['value'] == 'shutdown' || $json_body['value'] == 'reboot' ) {
                    //Don't wait for shutdown or reboot commands since it will cause a response to not be returned
                  $result = array( 'code' => 0, 'result' => ['SUCCESS'] );
                  echo json_encode($result);
                  http_response_code(200);
                  exec(sprintf('%s \'%s\' > /dev/null &', _CMD, escapeshellcmd($json_body['value'])), $return_text, $result_int);
                  die('');
                } else {
                  exec(sprintf('%s \'%s\'', _CMD, escapeshellcmd($json_body['value'])), $return_text, $result_int);
                }
            } else {
                http_response_code(400);
                die('BAD REQUEST');
            }
        } else {
            http_response_code(400);
            die('BAD REQUEST');
        }
    } else {
        http_response_code(405);
        die('METHOD NOT SUPPORTED');
    }
    $result = array( 'code' => $result_int, 'result' => $return_text );
    echo json_encode($result);
} else {
    http_response_code(404);
    die('NOT FOUND');
}
