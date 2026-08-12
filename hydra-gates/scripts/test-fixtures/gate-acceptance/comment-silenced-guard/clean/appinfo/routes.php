<?php
/**
 * @license EUPL-1.2
 * @copyright Conduction B.V.
 */

return [
	'routes' => [
		['name' => 'webhook#rotate',     'url' => '/api/agents/{id}/webhook', 'verb' => 'POST'],
		['name' => 'webhook#readOwned',  'url' => '/api/agents/{id}/webhook', 'verb' => 'GET'],
		['name' => 'theme#show',         'url' => '/api/themes/{id}',         'verb' => 'GET'],
		['name' => 'theme#showShared',   'url' => '/api/themes/{id}/shared',  'verb' => 'GET'],
	],
];
