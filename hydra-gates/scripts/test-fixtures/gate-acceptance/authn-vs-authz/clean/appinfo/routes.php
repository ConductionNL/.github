<?php
/**
 * @license EUPL-1.2
 * @copyright Conduction B.V.
 */

return [
	'routes' => [
		['name' => 'ledger#ownershipCheck', 'url' => '/api/entries/{entryId}',              'verb' => 'GET'],
		['name' => 'ledger#tenancy404',     'url' => '/api/entries/{entryId}/tenancy',      'verb' => 'GET'],
		['name' => 'ledger#collaborator',   'url' => '/api/entries/{entryId}/collaborator', 'verb' => 'GET'],
		['name' => 'ledger#handoff',        'url' => '/api/entries/{entryId}/handoff',      'verb' => 'GET'],
	],
];
