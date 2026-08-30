import { atom } from "jotai";
import type { User } from "./types";

export const userAtom = atom<User | null>(null);
export const authResolvedAtom = atom(false);
