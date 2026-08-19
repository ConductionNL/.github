<?php
/**
 * @license EUPL-1.2
 * @copyright Conduction B.V.
 */

return [
	'routes' => [
		['name' => 'catalogue#arbitraryId',  'url' => '/api/themes/{id}',              'verb' => 'GET'],
		['name' => 'catalogue#listing',      'url' => '/api/themes',                   'verb' => 'GET'],
		['name' => 'catalogue#byToken',      'url' => '/api/shares/{shareToken}',      'verb' => 'GET'],
		['name' => 'catalogue#rawBodyDispatch', 'url' => '/api/soap/cases',           'verb' => 'POST'],
	],
];
