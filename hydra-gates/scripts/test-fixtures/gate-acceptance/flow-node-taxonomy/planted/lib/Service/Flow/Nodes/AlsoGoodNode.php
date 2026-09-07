<?php
declare(strict_types=1);
namespace OCA\Example\Service\Flow\Nodes;

use OCA\Example\Service\Flow\IFlowNode;
use OCA\Example\Service\Flow\IFlowNodeTaxonomy;

/** Beside the planted one, so the gate is shown to refuse ONE and not the directory. */
class AlsoGoodNode implements IFlowNode, IFlowNodeTaxonomy {
	public function getKind(): string { return 'gateway'; }
	public function getCategory(): string { return 'logic'; }
}//end class
