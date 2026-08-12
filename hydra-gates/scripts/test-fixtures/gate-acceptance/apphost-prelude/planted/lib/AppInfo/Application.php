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
 * The gate-64 mechanism, and nothing else: an AppHost adoption resolved
 * DURING register(), with no ADR-040 autoload prelude above it.
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
        Bootstrap::registerGenerics($context, self::APP_ID);

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
