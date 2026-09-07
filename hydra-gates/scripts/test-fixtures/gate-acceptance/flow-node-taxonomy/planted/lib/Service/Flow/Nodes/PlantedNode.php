<?php
declare(strict_types=1);
namespace OCA\Example\Service\Flow\Nodes;

use OCA\Example\Service\Flow\IFlowNode;

/**
 * THE PLANTED NODE. It contributes a step and says nothing about what kind of
 * step it is, so the palette serves it as serviceTask/other — a guess that
 * looks answered. The gate must refuse this file.
 */
class PlantedNode implements IFlowNode {
}//end class
