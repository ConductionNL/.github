<?php
declare(strict_types=1);
namespace OCA\Example\Service\Flow\Nodes;

use OCA\Example\Service\Flow\IFlowNode;
use OCA\Example\Service\Flow\IFlowNodeTaxonomy;

/** A node that says what kind of step it is. */
class GoodNode implements IFlowNode, IFlowNodeTaxonomy {
	public function getKind(): string { return 'serviceTask'; }
	public function getCategory(): string { return 'objects'; }
}//end class
