let graph;
let widget;
let eventNamesVisible = false;
let eventParamVisible = false;
let actionsProhibited = false;
let isDeleting = false;

const WHITELISTED_PARAMS = new Set(['MessageId', 'ASName']);

function getNodeLabel(node) {
  const prefix = eventNamesVisible ? `${node.data.name}\n` : '';
  let label = node.id;

  if (node.node_type === 'entry') {
    label = `${node.data.name}`;
  }
  else if (node.node_type === 'action') {
    label = `${prefix}${node.data.actor}\n${node.data.action}`;
  }
  else if (node.node_type === 'switch') {
    label = `${prefix}${node.data.actor}\n${node.data.query}`;
  }
  else if (node.node_type === 'fork') {
    label = `${prefix}Fork`;
  }
  else if (node.node_type === 'join') {
    label = `${prefix}Join`;
  }
  else if (node.node_type === 'sub_flow') {
    label = `${prefix}${node.data.res_flowchart_name}\n<${node.data.entry_point_name}>`;
  }

  if (eventParamVisible && node.data.params) {
    let i = 0;
    let hasMore = false;
    for (const [key, value] of Object.entries(node.data.params)) {
      if (key === 'IsWaitFinish') {
        continue;
      }
      const isWhitelisted = WHITELISTED_PARAMS.has(key);
      if (!isWhitelisted && i >= 5) {
        hasMore = true;
      } else {
        const valueStr = typeof value === 'number' ? value.toFixed(6).replace(/\.?0*$/, '') : value;
        label += `\n${key}: ${valueStr}`;
      }
      i++;
    }
    if (hasMore) {
      label += '\n...';
    }
  }
  return label;
}

function handleNodeContextMenu(id) {
  const actions = [];

  const idx = parseInt(id, 10);
  const node = graph.g.node(id);
  const prevNodes = [...(new Set(graph.g.inEdges(id).filter(e => !graph.g.edge(e).virtual).map(e => parseInt(e.v, 10))))];
  const nextNodes = [...(new Set(graph.g.outEdges(id).filter(e => !graph.g.edge(e).virtual).map(e => parseInt(e.w, 10))))];
  const classes = node.class.split(' ');

  const addAction = (name, fn) => actions.push({ title: name, action: () => { setTimeout(fn, 60) } });

  if (!actionsProhibited) {
    if (idx >= 0) { // Event actions
      if (!classes.includes('fork') && !classes.includes('join')) {
        addAction('Edit event...', () => widget.editEvent(idx));
      }
      if (classes.includes('switch')) {
        addAction('Edit cases...', () => widget.editSwitchBranches(idx));
      }
      if (classes.includes('fork')) {
        addAction('Edit branches...', () => widget.editForkBranches(idx));
      }
      if (!classes.includes('join')) {
        actions.push({ divider: true });
      }

      addAction('Add entry point here...', () => widget.addEntryPoint(idx));
      actions.push({ divider: true });

      if (!classes.includes('join')) {
        addAction('Add new parent...', () => widget.addEventAbove(prevNodes, idx));
      }

      if (classes.includes('action') || classes.includes('sub_flow') || classes.includes('join')) {
        addAction('Add new child...', () => widget.addEventBelow(idx));
        if (nextNodes.length) {
          addAction('Unlink child', () => widget.unlink(idx));
        } else {
          addAction('Link to event...', () => widget.link(idx));
        }
      }

      const oneBranchSwitchOrFork =
          nextNodes.length <= 1 && (classes.includes('fork') || classes.includes('switch'));
      const isOnlyEventInEntry =
          nextNodes.length === 0 && prevNodes.length === 1 && parseInt(prevNodes[0], 10) <= -1000;

      if (!isOnlyEventInEntry && (classes.includes('action') || classes.includes('sub_flow') || oneBranchSwitchOrFork)) {
        actions.push({ divider: true });
        addAction('Remove event', () => {
          isDeleting = true;
          widget.removeEvent(prevNodes, idx);
        });
      }

    } else { // Entry point actions
      addAction('Remove entry point', () => widget.removeEntryPoint(idx));
    }

    actions.push({ divider: true });
  }

  if (graph.persistentWhitelist) {
    addAction('Show all events', () => graph.renderOnlyConnected());
  } else {
    addAction('Show only connected events', () => graph.renderOnlyConnected(id));
  }

  return actions;
}

class Renderer {
  constructor() {
    this.svg = d3.select('svg');
    this.svgGroup = d3.select('svg g');

    this.nodeWhitelist = null;

    this.zoom = d3.behavior.zoom();
    this.lastZoomEventStart = null;
    this.svg.call(this.zoom.on('zoom', () => this.updateTransform()));
    this.svg.call(this.zoom.on('zoomstart', () => this.lastZoomEventStart = new Date()));

    // Reset selection on click.
    // Unfortunately we need to do some extra work to determine whether the click event is caused
    // by zooming or is a simple click.
    this.svg.on('click', () => {
      // The zoom lasted more than 100 ms, so it's likely a zoom.
      if ((new Date() - this.lastZoomEventStart) >= 100) {
        return;
      }
      this.clearSelection();
    });
  }

  getSelection() {
    const selected = d3.select('.selected');
    return selected.empty() ? -1 : parseInt(selected.attr('id').slice(1), 10);
  }

  clearSelection() {
    widget.emitEventSelectedSignal(-1);
    this.clearSelectionWithoutEmittingSignal();
  }

  clearSelectionWithoutEmittingSignal() {
    const selected = this.getSelection();
    if (selected !== -1) {
      const node = graph.g.node(selected);
      node.class = node.class.replace(/\bselected\b/, '');
    }
    for (const cl of ['selected', 'selected-in-edge', 'selected-out-edge', 'selected-in-edge-label', 'selected-out-edge-label']) {
      d3.selectAll('.' + cl).classed(cl, false);
    }
  }

  select(id, g) {
    this.clearSelectionWithoutEmittingSignal();
    d3.select(`#n${id}`).classed('selected', true);
    g.node(id).class += ' selected';
    g.inEdges(id).forEach((e) => {
      d3.selectAll(`.edge-${e.v}-${e.w}`).classed('selected-in-edge', true);
      d3.select(`#label-${e.name}`).classed('selected-in-edge-label', true);
    });
    g.outEdges(id).forEach((e) => {
      d3.selectAll(`.edge-${e.v}-${e.w}`).classed('selected-out-edge', true);
      d3.select(`#label-${e.name}`).classed('selected-out-edge-label', true);
    });
    widget.emitEventSelectedSignal(parseInt(id, 10));
  }

  getElement(id) {
    const element = d3.select(`#n${id}`);
    return element.empty() ? null : element;
  }

  scrollTo(id, center=false, duration=1000) {
    const element = this.getElement(id);
    if (!element) {
      return false;
    }
    const t = d3.transform(element.attr('transform'));
    const [x, y] = t.translate;
    const scale = this.zoom.scale();
    const newY = y*-scale + (center ? (window.innerHeight/2) : 60);
    this.svg.transition().duration(duration)
      .call(this.zoom.translate([x*-scale + window.innerWidth/2, newY]).event);
    return true;
  }

  render(g) {
    const visibleGraph = new graphlib.Graph({ multigraph: true });
    visibleGraph.setGraph({});
    visibleGraph.graph().transition = (selection) => {
      return selection.transition().duration(500);
    };

    for (const v of g.nodes()) {
      if (!this.nodeWhitelist || this.nodeWhitelist.has(v)) {
        visibleGraph.setNode(v, g.node(v));
      }
    }
    for (const e of g.edges()) {
      if (!this.nodeWhitelist || this.nodeWhitelist.has(e.v)) {
        visibleGraph.setEdge(e, g.edge(e));
      }
    }

    const render = dagreD3.render();
    this.svgGroup.call(render, visibleGraph);
    this.svgGroup.selectAll('.node')
      .on('click', (id) => {
        this.select(id, g);
        d3.event.stopPropagation();
      })
      .on('dblclick', (id) => {
        if (actionsProhibited) {
          d3.event.stopPropagation();
          return;
        }

        const node = g.node(id);
        const classes = node.class.split(' ');
        if (classes.includes('fork')) {
          widget.editForkBranches(parseInt(id, 10));
        } else {
          widget.editEvent(parseInt(id, 10));
        }
        d3.event.stopPropagation();
      })
      .on('contextmenu', d3.contextMenu(handleNodeContextMenu));
  }

  setScale(scale) { this.zoom.scale(scale); this.updateTransform(); }
  setTranslate(translate) { this.zoom.translate(translate); this.updateTransform(); }

  updateTransform() {
    this.svgGroup.attr('transform', `translate(${this.zoom.translate()})scale(${this.zoom.scale()})`);
  }
}

class Graph {
  constructor() {
    this.g = null;
    this.data = null;
    this.renderer = new Renderer();
    this.persistentWhitelist = null;
  }

  update(data) {
    this.data = data;
    this.g = new graphlib.Graph({ multigraph: true });
    this.g.setGraph({});

    for (const entry of data) {
      if (entry.type === 'node') {
        this.g.setNode(entry.id, {
          label: getNodeLabel(entry),
          'class': entry.node_type,
          id: `n${entry.id}`,
          idx: entry.id,
          name: entry.data.name,
        });
      } else if (entry.type === 'edge') {
        this.g.setEdge(entry.source, entry.target, {
          labelType: 'html',
          label: `<span id="label-edge-${entry.source}-${entry.target}-${entry.data.value}">${entry.data.value == null ? '' : entry.data.value}</span>`,
          'class': `edge-${entry.source}-${entry.target}`,
          virtual: !!entry.data.virtual,
        }, `edge-${entry.source}-${entry.target}-${entry.data.value}`);
      }
    }
  }

  refresh() {
    if (this.data && Object.keys(this.data).length > 0) {
      this.update(this.data);
    }
  }

  render() {
    if (this.persistentWhitelist) {
      this.renderer.nodeWhitelist = new Set(this.g.nodes()
        .map(idx => this.g.node(idx))
        .filter(node => this.persistentWhitelist.has(node.name))
        .map(node => node.idx.toString())
      );
    } else {
      this.renderer.nodeWhitelist = null;
    }

    this.renderer.render(this.g);
  }

  renderOnlyConnected(v) {
    const selected = this.renderer.getSelection();
    this.persistentWhitelist = this.findNodeComponent(v);
    this.render();
    if (v != null) {
      setTimeout(() => this.renderer.scrollTo(v), 500);
    } else if (selected !== -1) {
      setTimeout(() => this.renderer.scrollTo(selected), 500);
    }
  }

  /// Returns a set of connected events: {"Event123", "Event125", "EntryPoint", ...}
  findNodeComponent(v) {
    const components = graphlib.alg.components(this.g);
    const c = components.find((component) => component.includes(v));
    if (!c) {
      return null;
    }
    return new Set(c.map(idx => this.g.node(idx).name));
  }
}

graph = new Graph();

document.body.addEventListener('keydown', (event) => {
  const key = event.key; // "ArrowRight", "ArrowLeft", "ArrowUp", or "ArrowDown"

  if (key === 'Escape') {
    graph.renderer.clearSelection();
    return;
  }

  // Handle zoom
  if (event.ctrlKey) {
    let scaleMultiplier = 1;
    if (key === 'ArrowUp')
      scaleMultiplier = 1.1;
    else if (key === 'ArrowDown')
      scaleMultiplier = 0.9;
    graph.renderer.setScale(graph.renderer.zoom.scale() * scaleMultiplier);
    if (scaleMultiplier !== 1)
      return;
  }

  // Handle translate / navigation
  const selected = graph.renderer.getSelection();
  if (selected === -1) {
    let vDirection = 0;
    let hDirection = 0;
    switch (key) {
      case 'ArrowUp':
        vDirection = 1;
        break;
      case 'ArrowDown':
        vDirection = -1;
        break;
      case 'ArrowLeft':
        hDirection = 1;
        break;
      case 'ArrowRight':
        hDirection = -1;
        break;
    }
    const [x, y] = graph.renderer.zoom.translate();
    graph.renderer.setTranslate([x + 100 * hDirection, y + 100 * vDirection]);
    return;
  }
  if (key === 'ArrowUp' || key === 'ArrowDown') {
    const nodes = key === 'ArrowUp' ? graph.g.predecessors(selected) : graph.g.successors(selected);
    if (nodes.length > 0) {
      graph.renderer.scrollTo(nodes[0], true, 500);
      graph.renderer.select(nodes[0], graph.g);
    }
  }
});

new QWebChannel(qt.webChannelTransport, (channel) => {
  widget = channel.objects.widget;

  function select(id) {
    if (graph.persistentWhitelist) {
      graph.renderOnlyConnected(id.toString());
      graph.renderer.select(id, graph.g);
    } else {
      graph.renderer.setScale(1);
      graph.renderer.select(id, graph.g);
      graph.renderer.scrollTo(id);
    }
  }

  function load(cb) {
    widget.getJson((data) => {
      if (!data) {
        return;
      }
      graph.update(data);
      graph.render();
      const selected = graph.renderer.getSelection();
      if (selected !== -1 && !isDeleting) {
        graph.renderer.scrollTo(selected);
      }
      widget.emitReloadedSignal();
      if (cb) {
        cb(data);
      }
      isDeleting = false;
    });
  }

  widget.flowDataChanged.connect(() => {
    load(() => {
      if (graph.renderer.getSelection() === -1 && !isDeleting) {
        graph.renderer.setTranslate([20, 20]);
      }
    });
  });

  widget.fileLoaded.connect(() => {
    graph.persistentWhitelist = null;
    graph.renderer.clearSelection();
  });

  widget.selectRequested.connect((id) => {
    select(id);
  });

  widget.eventNameVisibilityChanged.connect((visible) => {
    const previousValue = eventNamesVisible;
    eventNamesVisible = visible;
    if (!graph.g) {
      return;
    }
    if (visible !== previousValue) {
      graph.refresh();
      graph.render();
    }
  });

  widget.eventParamVisibilityChanged.connect((visible) => {
    const previousValue = eventParamVisible;
    eventParamVisible = visible;
    if (!graph.g) {
      return;
    }
    if (visible !== previousValue) {
      graph.refresh();
      graph.render();
    }
  });

  widget.actionProhibitionChanged.connect((value) => {
    actionsProhibited = value;
  });

  widget.emitReadySignal();
  load();
});
