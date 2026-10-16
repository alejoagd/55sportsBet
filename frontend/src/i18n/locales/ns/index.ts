// Diccionarios por pantalla (generados por archivo fuente). Cada uno exporta
// { es, en, pt, fr } con exactamente las mismas claves (en/pt/fr se tipan
// contra es, así que falta/sobra una clave = error de compilación).
import type { LangCode } from '../../index';

import competition from './competition';

import teamForm from './teamForm';

import matchDetail from './matchDetail';

import h2hScoring from './h2hScoring';

import h2hNarrative from './h2hNarrative';

import teamStats from './teamStats';

import bestBets from './bestBets';

import scoreRange from './scoreRange';

import evolution from './evolution';

import bettingLines from './bettingLines';

import bestBetsAnalysis from './bestBetsAnalysis';

export type NsBundle = Record<LangCode, Record<string, string>>;

export const nsBundles: Record<string, NsBundle> = {};
nsBundles.bestBetsAnalysis = bestBetsAnalysis;
nsBundles.bettingLines = bettingLines;
nsBundles.evolution = evolution;
nsBundles.scoreRange = scoreRange;
nsBundles.bestBets = bestBets;
nsBundles.teamStats = teamStats;
nsBundles.h2hNarrative = h2hNarrative;
nsBundles.h2hScoring = h2hScoring;
nsBundles.matchDetail = matchDetail;
nsBundles.teamForm = teamForm;
nsBundles.competition = competition;
