<?php
/**
 * @license EUPL-1.2
 * @copyright Conduction B.V.
 */

return [
	'routes' => [
		['name' => 'inspection#submitResult', 'url' => '/api/cases/{id}/inspection-result', 'verb' => 'POST'],
		['name' => 'inspection#purge',        'url' => '/api/cases/{id}/purge',             'verb' => 'POST'],
		['name' => 'inspection#prefs',        'url' => '/api/prefs/{userId}',               'verb' => 'GET'],
		['name' => 'inspection#join',         'url' => '/api/orgs/{uuid}/join',             'verb' => 'POST'],
	],
];
