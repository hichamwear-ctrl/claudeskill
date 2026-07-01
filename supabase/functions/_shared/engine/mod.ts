/**
 * Point d'entrée du moteur conversationnel pur (M2.3).
 * Les Edge Functions importent depuis ici : `converse` (avec adaptateur IA) et
 * `submit-request` (revalidation serveur) réutilisent le MÊME moteur.
 */
export { compute } from './engine.ts';
export { answerState, isMissing } from './validate.ts';
export { evalCondition, isRequired, isVisible } from './conditions.ts';
export type {
  Answers,
  AnswerState,
  AnswerValue,
  Condition,
  EngineConfig,
  EngineResult,
  Question,
  QuestionSet,
  QuestionType,
  Validation,
} from './types.ts';
