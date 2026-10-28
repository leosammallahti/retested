// The study typology: how each original study worked (data/curated/effect_typology.json, through wiki.json).
// Labels were given by two models from outcome-blind text, checked against a blind hand-coded sample, and read where
// the models disagreed; the plain names below are what readers see.
import { effectTypology } from './data';

export type Dim = 'study_kind' | 'outcome_kind' | 'who_studied' | 'setting' | 'body_brain_genes';

export const STUDY_KIND: Record<string, { name: string; short: string; about: string }> = {
  TRAINING_OR_THERAPY: { name: 'Training, therapy or reward', short: 'Training or therapy', about: 'People were taught a skill, given therapy, or rewarded for a behaviour.' },
  TRAIT_OR_GROUP: { name: 'Compares existing traits or groups', short: 'Traits or groups', about: 'Nothing was changed: the study compared people (or records) as they already were.' },
  TASK_OR_FRAMING: { name: 'Changes the task or its wording', short: 'Task or wording', about: 'The researchers changed the task, the words or the options, and measured that same task.' },
  NUDGE_OR_SPILLOVER: { name: 'Small cue that spills over', short: 'Cue or spillover', about: 'A passing cue, mood, posture, drink or earlier task was claimed to change a separate later judgment or act.' },
};
export const OUTCOME_KIND: Record<string, { name: string; short: string; about: string }> = {
  ACTION_OR_CHOICE: { name: 'What people actually did or chose', short: 'Actions or choices', about: 'Choices, behaviour, money given, food eaten: what people (or animals) actually did.' },
  PERFORMANCE: { name: 'Speed, accuracy or memory', short: 'Speed or accuracy', about: 'A score on a task: how fast, how accurate, how much was remembered.' },
  SELF_REPORT_OR_RATING: { name: 'What people said or rated', short: 'Self-reports', about: 'Answers on a questionnaire, a rating, or an estimate.' },
  BRAIN_BODY_OR_RECORD: { name: 'Brain, body or official records', short: 'Brain, body or records', about: 'A brain scan, genes, hormones, heart rate, or official records such as deaths or court files.' },
};
export const WHO: Record<string, string> = {
  ADULTS: 'Adults', CHILDREN_AND_TEENS: 'Children and teens', BABIES_UNDER_3: 'Babies and toddlers',
  MENTAL_HEALTH_PATIENTS: 'People in care for a mental health condition', AUTISTIC_OR_DISABLED: 'Autistic or disabled people', ANIMALS: 'Animals',
};
export const SETTING: Record<string, string> = {
  NONE_OR_LAB: 'Lab, online or everyday life', SCHOOL: 'Schools', CLINIC_OR_HOSPITAL: 'Clinics and hospitals',
  WORKPLACE: 'Workplaces', COURTS_OR_PRISONS: 'Courts and prisons',
};

// Grid order: rows from the kinds of study that held up most often to least, as measured on the blind sample.
export const STUDY_ORDER = ['TRAINING_OR_THERAPY', 'TRAIT_OR_GROUP', 'TASK_OR_FRAMING', 'NUDGE_OR_SPILLOVER'];
export const OUTCOME_ORDER = ['ACTION_OR_CHOICE', 'PERFORMANCE', 'SELF_REPORT_OR_RATING', 'BRAIN_BODY_OR_RECORD'];

export const typologyFor = (slug: string) => effectTypology(slug);
