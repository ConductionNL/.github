<?php
/**
 * @license EUPL-1.2
 * @copyright Conduction B.V.
 */

return [
	'routes' => [
		['name' => 'ledger#bare',                  'url' => '/api/entries/{entryId}/bare',      'verb' => 'GET'],
		['name' => 'ledger#preamble',              'url' => '/api/entries/{entryId}/preamble',  'verb' => 'GET'],
		['name' => 'ledger#preambleForbiddenCode', 'url' => '/api/entries/{entryId}/forbidden', 'verb' => 'GET'],
		['name' => 'ledger#castCallerValue',       'url' => '/api/entries/{entryId}/cast/{targetUid}', 'verb' => 'GET'],
		['name' => 'ledger#readAsOwner',           'url' => '/api/entries/{entryId}',           'verb' => 'GET'],
	],
];
