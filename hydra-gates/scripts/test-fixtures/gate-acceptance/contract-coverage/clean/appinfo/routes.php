<?php
return [
    'routes' => [
        ['name' => 'thing#listThings',     'url' => '/api/things',       'verb' => 'GET'],
        ['name' => 'thing#adminOnlyPurge', 'url' => '/api/things/purge', 'verb' => 'POST'],
        ['name' => 'thing#farAttribute',   'url' => '/api/things/far',   'verb' => 'GET'],
    ],
];
