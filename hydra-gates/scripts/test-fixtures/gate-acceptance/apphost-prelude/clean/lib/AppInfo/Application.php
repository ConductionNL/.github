<?php
/**
 * Application bootstrap.
 *
 * @license  EUPL-1.2
 * @copyright 2026 Conduction B.V.
 */

namespace OCA\AppHostFx\AppInfo;

use OCA\OpenRegister\AppHost\Bootstrap;
use OCP\AppFramework\App;
use OCP\AppFramework\Bootstrap\IBootContext;
use OCP\AppFramework\Bootstrap\IBootstrap;
use OCP\AppFramework\Bootstrap\IRegistrationContext;

/**
 * The clean arm. The AppHost adoption is IDENTICAL to the planted arm's —
 * same import, same call, same position inside register(). Only the ADR-040
 * prelude is added above it, so this pair tests whether gate-64 reads the
 * prelude and not merely whether it can spot an AppHost name.
 */
class Application extends App implements IBootstrap
{

    public const APP_ID = 'apphostfx';


    /**
     * Constructor.
     */
    public function __construct()
    {
        parent::__construct(self::APP_ID);

    }//end __construct()


    /**
     * Registers the app.
     *
     * @param IRegistrationContext $context The registration context.
     *
     * @return void
     */
    public function register(IRegistrationContext $context): void
    {
        try {
            $orPath = \OCP\Server::get(\OCP\App\IAppManager::class)->getAppPath('openregister');
            \OC_App::registerAutoloading('openregister', $orPath);
        } catch (\Throwable) {
            // OpenRegister absent or disabled — fall through to the degraded path.
        }

        Bootstrap::registerGenerics($context, self::APP_ID);

        // THE ANTI-WIDENING NEAR-MISS. A lazy service closure that MENTIONS an
        // AppHost class. Its body runs at resolution time, long after every app
        // has registered, so the prefix is on the autoloader by then and this
        // is correct code. A gate-64 that matched on the NAME rather than on
        // what register() actually resolves would report it.
        $context->registerService(
            'apphostfx.reader',
            function () {
                return new \OCA\OpenRegister\AppHost\Reader();
            }
        );

    }//end register()


    /**
     * Boots the app.
     *
     * @param IBootContext $context The boot context.
     *
     * @return void
     */
    public function boot(IBootContext $context): void
    {

    }//end boot()


}//end class
