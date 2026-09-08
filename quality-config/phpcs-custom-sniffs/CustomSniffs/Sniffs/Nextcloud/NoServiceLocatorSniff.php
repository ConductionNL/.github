<?php

/**
 * Forbid run-time lookups on the global Nextcloud container.
 *
 * Flags:
 *   \OC::$server->get(Foo::class)      \OC::$server->query(Foo::class)
 *   \OCP\Server::get(Foo::class)       OCP\Server::get(...)   Server::get(...) with `use OCP\Server;`
 *
 * Why this is an error and not a style preference. Inside a DI-built class such a
 * lookup is a hidden dependency no unit test can control. And outside a booted
 * Nextcloud (a unit test run from a source tree, a half-initialised bootstrap) the
 * global container knows none of the app's registrations, so it autowires the
 * requested service from scratch by reflection. Nextcloud's container has no cycle
 * detection: a constructor cycle recurses until memory runs out. On 2026-09-08 one
 * openregister unit test took 19 GB of RAM this way (openregister PR #3523).
 *
 * The replacement is constructor injection of the dependency itself, or, where the
 * lookup must stay lazy or dynamic, of `Psr\Container\ContainerInterface` (the app
 * container), which a test can hand a mock.
 *
 * Framework entry points that run before or outside DI (AppInfo, migrations, repair
 * steps) are excluded by pattern in the shared phpcs.xml, not here.
 *
 * @author  Conduction
 * @package CustomSniffs
 */

namespace CustomSniffs\Sniffs\Nextcloud;

use PHP_CodeSniffer\Files\File;
use PHP_CodeSniffer\Sniffs\Sniff;

/**
 * NoServiceLocatorSniff flags get()/query() on \OC::$server and \OCP\Server.
 */
class NoServiceLocatorSniff implements Sniff
{

    /**
     * Method names that resolve a service from the container.
     *
     * @var array<string>
     */
    private const LOCATOR_METHODS = ['get', 'query'];


    /**
     * Anchor on T_DOUBLE_COLON: both `\OC::$server` and `\OCP\Server::get` carry one.
     *
     * @return array<int>
     */
    public function register(): array
    {
        return [T_DOUBLE_COLON];
    }//end register()


    /**
     * Flag `\OC::$server->get(` / `->query(` and `\OCP\Server::get(`.
     *
     * @param File $phpcsFile The file being scanned.
     * @param int  $stackPtr  Position of the T_DOUBLE_COLON token.
     *
     * @return void
     */
    public function process(File $phpcsFile, $stackPtr): void
    {
        $tokens = $phpcsFile->getTokens();
        $prev = $phpcsFile->findPrevious(types: [T_WHITESPACE], start: ($stackPtr - 1), end: null, exclude: true);
        if ($prev === false) {
            return;
        }

        $subject = $this->classBefore(phpcsFile: $phpcsFile, ptr: $prev);
        if ($subject === 'OC') {
            $this->checkGlobalServer(phpcsFile: $phpcsFile, stackPtr: $stackPtr);
            return;
        }

        if ($subject === 'OCP\Server' || ($subject === 'Server' && $this->importsOcpServer(phpcsFile: $phpcsFile) === true)) {
            $this->checkStaticServer(phpcsFile: $phpcsFile, stackPtr: $stackPtr);
        }
    }//end process()


    /**
     * Reconstruct the class name that precedes `::`, without a leading backslash.
     *
     * Handles both the PHPCS 3 tokenisation (T_NS_SEPARATOR + T_STRING pairs) and
     * the PHP 8 single-token names (T_NAME_FULLY_QUALIFIED, T_NAME_QUALIFIED).
     *
     * @param File $phpcsFile The file being scanned.
     * @param int  $ptr       Position of the last token before `::`.
     *
     * @return string Class name such as `OC`, `OCP\Server` or `Server`.
     */
    private function classBefore(File $phpcsFile, int $ptr): string
    {
        $tokens = $phpcsFile->getTokens();
        $code = $tokens[$ptr]['code'];
        if (defined('T_NAME_FULLY_QUALIFIED') === true && $code === T_NAME_FULLY_QUALIFIED) {
            return ltrim($tokens[$ptr]['content'], '\\');
        }

        if (defined('T_NAME_QUALIFIED') === true && $code === T_NAME_QUALIFIED) {
            return $tokens[$ptr]['content'];
        }

        if ($code !== T_STRING) {
            return '';
        }

        $parts = [$tokens[$ptr]['content']];
        $i = ($ptr - 1);
        while ($i >= 0 && $tokens[$i]['code'] === T_NS_SEPARATOR) {
            if ($i >= 1 && $tokens[($i - 1)]['code'] === T_STRING) {
                array_unshift($parts, $tokens[($i - 1)]['content']);
                $i -= 2;
                continue;
            }

            break;
        }

        return implode('\\', $parts);
    }//end classBefore()


    /**
     * Whether the file has `use OCP\Server;` (with or without alias to Server).
     *
     * @param File $phpcsFile The file being scanned.
     *
     * @return bool
     */
    private function importsOcpServer(File $phpcsFile): bool
    {
        $tokens = $phpcsFile->getTokens();
        $ptr = 0;
        while (($ptr = $phpcsFile->findNext(types: [T_USE], start: $ptr)) !== false) {
            $end = $phpcsFile->findNext(types: [T_SEMICOLON], start: $ptr);
            if ($end === false) {
                return false;
            }

            $statement = trim(str_replace(' ', '', $phpcsFile->getTokensAsString(start: ($ptr + 1), length: ($end - $ptr - 1))));
            if ($statement === 'OCP\Server' || $statement === '\OCP\Server' || str_starts_with($statement, 'OCP\Server as') === true) {
                return true;
            }

            $ptr = ($end + 1);
        }

        return false;
    }//end importsOcpServer()


    /**
     * `\OC::$server->get(` or `->query(`.
     *
     * @param File $phpcsFile The file being scanned.
     * @param int  $stackPtr  Position of the `::` token.
     *
     * @return void
     */
    private function checkGlobalServer(File $phpcsFile, int $stackPtr): void
    {
        $tokens = $phpcsFile->getTokens();
        $var = $phpcsFile->findNext(types: [T_WHITESPACE], start: ($stackPtr + 1), end: null, exclude: true);
        if ($var === false || $tokens[$var]['code'] !== T_VARIABLE || $tokens[$var]['content'] !== '$server') {
            return;
        }

        $arrow = $phpcsFile->findNext(types: [T_WHITESPACE], start: ($var + 1), end: null, exclude: true);
        if ($arrow === false || ($tokens[$arrow]['code'] !== T_OBJECT_OPERATOR && $tokens[$arrow]['code'] !== T_NULLSAFE_OBJECT_OPERATOR)) {
            return;
        }

        $method = $phpcsFile->findNext(types: [T_WHITESPACE], start: ($arrow + 1), end: null, exclude: true);
        $this->flagIfLocatorCall(phpcsFile: $phpcsFile, methodPtr: $method, reportPtr: $stackPtr, form: '\OC::$server->%s()');
    }//end checkGlobalServer()


    /**
     * `\OCP\Server::get(` or `::query(`.
     *
     * @param File $phpcsFile The file being scanned.
     * @param int  $stackPtr  Position of the `::` token.
     *
     * @return void
     */
    private function checkStaticServer(File $phpcsFile, int $stackPtr): void
    {
        $method = $phpcsFile->findNext(types: [T_WHITESPACE], start: ($stackPtr + 1), end: null, exclude: true);
        $this->flagIfLocatorCall(phpcsFile: $phpcsFile, methodPtr: $method, reportPtr: $stackPtr, form: '\OCP\Server::%s()');
    }//end checkStaticServer()


    /**
     * Add the error when the method token is get( or query(.
     *
     * @param File      $phpcsFile The file being scanned.
     * @param int|false $methodPtr Position of the method name token, or false.
     * @param int       $reportPtr Token to report the error on.
     * @param string    $form      Printf form of the call for the message.
     *
     * @return void
     */
    private function flagIfLocatorCall(File $phpcsFile, int|false $methodPtr, int $reportPtr, string $form): void
    {
        $tokens = $phpcsFile->getTokens();
        if ($methodPtr === false || $tokens[$methodPtr]['code'] !== T_STRING) {
            return;
        }

        $name = $tokens[$methodPtr]['content'];
        if (in_array($name, self::LOCATOR_METHODS, true) === false) {
            return;
        }

        $paren = $phpcsFile->findNext(types: [T_WHITESPACE], start: ($methodPtr + 1), end: null, exclude: true);
        if ($paren === false || $tokens[$paren]['code'] !== T_OPEN_PARENTHESIS) {
            return;
        }

        $phpcsFile->addError(
            'Global container lookup ' . sprintf($form, $name) . '. Inject the dependency, or Psr\Container\ContainerInterface, through the constructor. Outside a booted Nextcloud this autowires from scratch and can recurse until memory runs out (openregister #3523).',
            $reportPtr,
            'GlobalContainerLookup'
        );
    }//end flagIfLocatorCall()
}//end class
