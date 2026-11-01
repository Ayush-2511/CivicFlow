import React, { useState } from 'react';
import { HelpCircle, Send, AlertCircle, ChevronDown } from 'lucide-react';
import { InterviewQuestion } from '../types';

interface InterviewCardProps {
  questions: InterviewQuestion[];
  onSubmit: (answers: Record<string, any>, units: Record<string, string>) => void;
  isSubmitting: boolean;
  language: string;
}

const FIELD_LABELS: Record<string, Record<string, string>> = {
  business_type: {
    en: "What is your enterprise classification?",
    hi: "आपके व्यवसाय/उद्यम का प्रकार क्या है?",
    mr: "तुमच्या व्यवसायाचा / उद्योगाचा प्रकार काय आहे?",
  },
  annual_turnover: {
    en: "What is your business annual turnover in INR?",
    hi: "आपके व्यवसाय का वार्षिक टर्नओवर (रुपये में) कितना है?",
    mr: "तुमच्या व्यवसायाची वार्षिक उलाढाल (रुपयांमध्ये) किती आहे?",
  },
  annual_income: {
    en: "What is your total annual household income in INR?",
    hi: "आपकी कुल वार्षिक पारिवारिक आय (रुपये में) कितनी है?",
    mr: "तुमचे एकूण वार्षिक कौटुंबिक उत्पन्न (रुपयांमध्ये) किती आहे?",
  },
  land_hectares: {
    en: "How many hectares of cultivable land do you own?",
    hi: "आपके पास कितनी हेक्टेयर कृषि भूमि है? (1 हेक्टेयर = 2.47 एकड़)",
    mr: "तुमच्याकडे किती हेक्टर शेतजमीन आहे? (१ हेक्टर = २.४७ एकर)",
  },
  occupation: {
    en: "What is your primary occupation?",
    hi: "आपका मुख्य व्यवसाय क्या है?",
    mr: "तुमचा मुख्य व्यवसाय कोणता आहे?",
  },
  state: {
    en: "Which state or union territory do you reside in?",
    hi: "आप किस राज्य या केंद्र शासित प्रदेश के निवासी हैं?",
    mr: "तुम्ही कोणत्या राज्यात किंवा केंद्रशासित प्रदेशात राहता?",
  },
};

const DEFAULT_OPTIONS: Record<string, string[]> = {
  business_type: ["Micro", "Small", "Medium", "Proprietorship", "Partnership", "Other"],
  occupation: [
    "Small Business Owner",
    "Micro Enterprise",
    "Farmer",
    "Retail Trade",
    "Artisan",
    "Student",
    "Self Help Group",
    "Other",
  ],
};

const OPTION_LABELS: Record<string, Record<string, string>> = {
  Micro: { en: "Micro Enterprise", hi: "Micro (सूक्ष्म उद्यम)", mr: "Micro (सूक्ष्म उद्योग)" },
  Small: { en: "Small Enterprise", hi: "Small (लघु उद्यम)", mr: "Small (लघु उद्योग)" },
  Medium: { en: "Medium Enterprise", hi: "Medium (मध्यम उद्यम)", mr: "Medium (मध्यम उद्योग)" },
  Proprietorship: { en: "Proprietorship", hi: "एकल स्वामित्व", mr: "एकल मालकी (Proprietorship)" },
  Partnership: { en: "Partnership", hi: "भागीदारी", mr: "भागीदारी (Partnership)" },
  "Small Business Owner": { en: "Small Business Owner", hi: "छोटा व्यापारी / व्यवसाय", mr: "लहान व्यावसायिक" },
  "Micro Enterprise": { en: "Micro Enterprise", hi: "सूक्ष्म उद्योग", mr: "सूक्ष्म उद्योग" },
  Farmer: { en: "Farmer / Agriculture", hi: "किसान / कृषि", mr: "शेतकरी / शेती" },
  "Retail Trade": { en: "Retail Trade / Shopkeeper", hi: "खुदरा व्यापार / दुकानदार", mr: "किरकोळ व्यापारी / दुकानदार" },
  Artisan: { en: "Artisan / Craftsman", hi: "कारीगर / शिल्पकार", mr: "कारागीर / शिल्पकार" },
  "Self Help Group": { en: "Self Help Group (SHG)", hi: "स्वयं सहायता समूह", mr: "बचत गट (SHG)" },
  Student: { en: "Student", hi: "छात्र / विद्यार्थी", mr: "विद्यार्थी" },
  Other: { en: "Other (Specify)", hi: "Other (अन्य)", mr: "Other (इतर)" },
};

export const InterviewCard: React.FC<InterviewCardProps> = ({
  questions,
  onSubmit,
  isSubmitting,
  language,
}) => {
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [units, setUnits] = useState<Record<string, string>>({});
  const [validationError, setValidationError] = useState<string | null>(null);
  const [customOthers, setCustomOthers] = useState<Record<string, string>>({});

  const handleInputChange = (field: string, val: any) => {
    setAnswers((prev) => ({ ...prev, [field]: val }));
    setValidationError(null);
  };

  const handleUnitChange = (field: string, unitVal: string) => {
    setUnits((prev) => ({ ...prev, [field]: unitVal }));
  };

  const handleCustomOtherChange = (field: string, customVal: string) => {
    setCustomOthers((prev) => ({ ...prev, [field]: customVal }));
    setAnswers((prev) => ({ ...prev, [field]: customVal || 'Other' }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const answeredCount = Object.keys(answers).filter(
      (k) => answers[k] !== undefined && answers[k] !== ''
    ).length;

    if (answeredCount === 0) {
      setValidationError(
        language === 'mr'
          ? 'कृपया पात्रतेचे मूल्यांकन करण्यासाठी खालील प्रश्नांची उत्तरे द्या.'
          : language === 'hi'
          ? 'कृपया अपनी पात्रता की जांच करने के लिए नीचे दिए गए प्रश्नों के उत्तर दें।'
          : 'Please answer the questions below to evaluate your eligibility.'
      );
      return;
    }

    onSubmit(answers, units);
  };

  const getQuestionLabel = (q: InterviewQuestion): string => {
    const f = q.field;
    const langKey = ['hi', 'mr', 'en'].includes(language) ? language : 'en';
    if (FIELD_LABELS[f] && FIELD_LABELS[f][langKey]) {
      return FIELD_LABELS[f][langKey];
    }
    return q.question_text || f.replace(/_/g, ' ');
  };

  const getOptionLabel = (opt: string): string => {
    const langKey = ['hi', 'mr', 'en'].includes(language) ? language : 'en';
    if (OPTION_LABELS[opt] && OPTION_LABELS[opt][langKey]) {
      return OPTION_LABELS[opt][langKey];
    }
    return opt;
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border-2 border-amber-300 p-5 sm:p-6 mb-6">
      <div className="flex items-center space-x-2.5 mb-4">
        <div className="p-2 bg-amber-100 text-amber-800 rounded-lg">
          <HelpCircle className="w-5 h-5" />
        </div>
        <div>
          <span className="text-xs font-bold text-amber-700 uppercase tracking-wider">
            {language === 'mr' ? 'अतिरिक्त माहिती आवश्यक' : language === 'hi' ? 'अतिरिक्त जानकारी आवश्यक' : 'Human-in-the-Loop Interaction'}
          </span>
          <h3 className="text-base font-bold text-slate-800">
            {language === 'mr' ? 'पात्रता पडताळणीसाठी प्रश्नांची उत्तरे द्या' : language === 'hi' ? 'पात्रता सत्यापन के लिए उत्तर दें' : 'A Few Details Needed for Verification'}
          </h3>
          <p className="text-xs text-slate-500">
            {language === 'mr'
              ? 'या योजनेच्या नियमांनुसार फक्त आवश्यक असलेल्या फील्डसाठी प्रश्न विचारले आहेत.'
              : language === 'hi'
              ? 'इस नीति के नियमों के अनुसार केवल आवश्यक फ़ील्ड के लिए प्रश्न पूछे गए हैं।'
              : 'The AI state machine paused to ask only the missing fields required by this policy.'}
          </p>
        </div>
      </div>

      {validationError && (
        <div className="mb-4 p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{validationError}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {questions.map((q, idx) => {
          const field = q.field;
          const isLand = field.includes('land') || field.includes('area');
          const isMoney = field.includes('income') || field.includes('turnover');
          const isBoolean = q.input_type === 'boolean';
          
          // Dropdown fields: any field other than numbers/money/land, or explicitly business_type/occupation/choice
          const isDropdown = !isMoney && !isLand && !isBoolean;

          let dropdownOptions: string[] = [];
          if (isDropdown) {
            if (q.choices && q.choices.length > 0) {
              dropdownOptions = [...q.choices];
            } else if (DEFAULT_OPTIONS[field]) {
              dropdownOptions = [...DEFAULT_OPTIONS[field]];
            } else {
              dropdownOptions = ["Micro", "Small", "Medium", "Other"];
            }
            if (!dropdownOptions.includes("Other")) {
              dropdownOptions.push("Other");
            }
          }

          return (
            <div key={idx} className="bg-slate-50 p-4 rounded-xl border border-slate-200">
              <label className="block text-sm font-semibold text-slate-800 mb-1.5">
                {getQuestionLabel(q)}
              </label>

              {/* Render Dropdown for choice/business_type/occupation */}
              {isDropdown && (
                <div className="space-y-2">
                  <div className="relative">
                    <select
                      value={answers[field] || ''}
                      onChange={(e) => handleInputChange(field, e.target.value)}
                      className="w-full px-3.5 py-2.5 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 font-medium text-slate-800 appearance-none pr-8 cursor-pointer"
                    >
                      <option value="">
                        -- {language === 'mr' ? 'पर्याय निवडा' : language === 'hi' ? 'विकल्प चुनें' : 'Select your classification'} --
                      </option>
                      {dropdownOptions.map((opt) => (
                        <option key={opt} value={opt}>
                          {getOptionLabel(opt)}
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="w-4 h-4 text-slate-400 absolute right-3 top-3.5 pointer-events-none" />
                  </div>

                  {answers[field] === 'Other' && (
                    <input
                      type="text"
                      value={customOthers[field] || ''}
                      onChange={(e) => handleCustomOtherChange(field, e.target.value)}
                      placeholder={
                        language === 'mr'
                          ? 'तुमचा प्रकार स्पष्ट करा (उदा. सूक्ष्म, स्टार्टअप)...'
                          : language === 'hi'
                          ? 'अपना प्रकार दर्ज करें (उदा. स्टार्टअप)...'
                          : 'Specify other category...'
                      }
                      className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-amber-500"
                    />
                  )}
                </div>
              )}

              {/* Boolean field */}
              {isBoolean && (
                <div className="flex space-x-3 mt-2">
                  <button
                    type="button"
                    onClick={() => handleInputChange(field, true)}
                    className={`flex-1 py-2 px-4 rounded-lg text-xs font-bold border transition ${
                      answers[field] === true
                        ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                        : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100'
                    }`}
                  >
                    {language === 'mr' ? 'होय (Yes)' : language === 'hi' ? 'हाँ (Yes)' : 'Yes'}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleInputChange(field, false)}
                    className={`flex-1 py-2 px-4 rounded-lg text-xs font-bold border transition ${
                      answers[field] === false
                        ? 'bg-rose-600 text-white border-rose-600 shadow-sm'
                        : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100'
                    }`}
                  >
                    {language === 'mr' ? 'नाही (No)' : language === 'hi' ? 'नहीं (No)' : 'No'}
                  </button>
                </div>
              )}

              {/* Number / Money / Land fields */}
              {!isDropdown && !isBoolean && (
                <div className="flex space-x-2 mt-2">
                  <input
                    type="text"
                    value={answers[field] || ''}
                    onChange={(e) => handleInputChange(field, e.target.value)}
                    placeholder={
                      isLand
                        ? 'e.g. 1.5 or 3.0'
                        : isMoney
                        ? 'e.g. 50,00,000 or 50 lakh'
                        : 'Enter your answer'
                    }
                    className="flex-1 px-3.5 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 bg-white"
                  />

                  {/* Unit Dropdowns */}
                  {isLand && (
                    <select
                      value={units[field] || 'hectares'}
                      onChange={(e) => handleUnitChange(field, e.target.value)}
                      className="text-xs bg-white border border-slate-300 rounded-lg px-2.5 py-2 font-medium focus:ring-2 focus:ring-amber-500"
                    >
                      <option value="hectares">{language === 'mr' ? 'हेक्टर (Hectares)' : 'Hectares'}</option>
                      <option value="acres">{language === 'mr' ? 'एकर (Acres)' : 'Acres'}</option>
                    </select>
                  )}

                  {isMoney && (
                    <select
                      value={units[field] || 'INR'}
                      onChange={(e) => handleUnitChange(field, e.target.value)}
                      className="text-xs bg-white border border-slate-300 rounded-lg px-2.5 py-2 font-medium focus:ring-2 focus:ring-amber-500"
                    >
                      <option value="INR">INR (₹)</option>
                      <option value="lakh">{language === 'mr' ? 'लाख (Lakh)' : 'Lakh'}</option>
                      <option value="crore">{language === 'mr' ? 'कोटी (Crore)' : 'Crore'}</option>
                    </select>
                  )}
                </div>
              )}
            </div>
          );
        })}

        <div className="pt-2">
          <button
            type="submit"
            disabled={isSubmitting}
            className={`w-full py-3 px-4 rounded-xl text-sm font-bold flex items-center justify-center space-x-2 text-white shadow-md transition ${
              isSubmitting
                ? 'bg-slate-400 cursor-not-allowed'
                : 'bg-amber-600 hover:bg-amber-700 active:scale-[0.99] shadow-amber-500/20'
            }`}
          >
            {isSubmitting ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>
                  {language === 'mr'
                    ? 'पात्रता मोजत आहे...'
                    : language === 'hi'
                    ? 'पात्रता की गणना की जा रही है...'
                    : 'Calculating Eligibility...'}
                </span>
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                <span>
                  {language === 'mr'
                    ? 'उत्तरे सबमिट करा आणि पात्रता तपासा'
                    : language === 'hi'
                    ? 'उत्तर सबमिट करें और पात्रता जांचें'
                    : 'Submit Answers & Calculate Eligibility'}
                </span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
