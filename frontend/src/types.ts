export interface User {
  email: string;
  fullName: string;
}

export interface EntityNode {
  id: string;
  label: string;
  type: string;
  description: string;
  // Position parameters for force visualizer
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

export interface RelationshipLink {
  source: string; // matches node label or id
  target: string; // matches node label or id
  relationship: string;
  description: string;
}

export interface Community {
  id: string;
  name: string;
  description: string;
  members: string[];
}

export interface Message {
  id: string;
  role: "user" | "bot";
  text: string;
  mode?: "graphrag" | "vector" | null;
  timestamp: string;
}
