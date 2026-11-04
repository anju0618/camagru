<?php
declare(strict_types=1);

function base_url(): string
{
    return rtrim(getenv('BASE_URL') ?: 'http://localhost:8002', '/');
}

/** Tiny SMTP client (no auth), enough for Mailpit / a local relay. */
function send_mail(string $to, string $subject, string $body): bool
{
    $from = getenv('MAIL_FROM') ?: 'camagru@localhost';
    $fp = @fsockopen(getenv('SMTP_HOST') ?: 'mailpit', (int) (getenv('SMTP_PORT') ?: 1025), $errno, $errstr, 5);
    if (!$fp) {
        error_log('mail: cannot connect to SMTP server');
        return false;
    }
    stream_set_timeout($fp, 5);
    $read = function () use ($fp): string {
        $out = '';
        while (($line = fgets($fp, 515)) !== false) {
            $out .= $line;
            if (isset($line[3]) && $line[3] === ' ') {
                break;
            }
        }
        return $out;
    };
    $cmd = function (string $c) use ($fp, $read): string {
        fwrite($fp, $c . "\r\n");
        return $read();
    };
    $clean = fn(string $s): string => str_replace(["\r", "\n"], '', $s); // no header injection
    $read();
    $cmd('HELO camagru');
    $cmd('MAIL FROM:<' . $clean($from) . '>');
    $cmd('RCPT TO:<' . $clean($to) . '>');
    $cmd('DATA');
    $body = preg_replace('/\r\n|\r|\n/', "\r\n", $body);
    $body = preg_replace('/^\./m', '..', $body);
    fwrite($fp, 'From: ' . $clean($from) . "\r\nTo: " . $clean($to) . "\r\nSubject: " . $clean($subject)
        . "\r\nMIME-Version: 1.0\r\nContent-Type: text/plain; charset=UTF-8\r\n"
        . "Content-Transfer-Encoding: 8bit\r\n\r\n" . $body . "\r\n.\r\n");
    $ok = str_starts_with($read(), '250');
    $cmd('QUIT');
    fclose($fp);
    return $ok;
}
