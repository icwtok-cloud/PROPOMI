export type Property={id:string;title:string;type:string;operation:string;price:number;currency:string;zone:string;city:string;country?:string;surface?:number;rooms?:number;bedrooms?:number;bathrooms?:number;parking?:boolean;pool?:boolean;balcony?:boolean;petFriendly?:boolean;credit?:boolean;freshness?:string;source?:string;sourceUrl?:string;image?:string;images?:string[];originPublishedAt?:string;description?:string;agencyId?:string;detectedAt?:string;lastSeenAt?:string;needsReview?:boolean;possibleDuplicateOf?:string|null;listingGroupId?:string|null};
export type IntentProfile={budget?:number;zones?:string[];types?:string[];operations?:string[];financing?:string;timeframe?:string;notes?:string};
export type Question={id:string;property_id:string;user_id:string;text:string;created_at:string;answered?:boolean;comment?:string};
export type EventName='property_view'|'property_save'|'property_compare'|'property_question'|'visit_request'|'offer_created'|'contact_requested'|'contact_shared'|'counter_offer_created'|'negotiation_started'|'operation_advanced'|'search_performed';
export type Offer={id:string;user_id:string;property_id:string;amount:number;currency:string;payment_form:string;capital?:number;timeframe?:string;comment?:string;status:string;created_at:string;contact_revealed:boolean;origin?:string|null;property_title?:string|null;property_zone?:string|null;listing_group_id?:string|null;buyer_name?:string;buyer_phone?:string;buyer_email?:string};
export type Subscription={id:string;agencyId:string;plan:string;cupoCiclo:number|null;consumidoCiclo:number;fechaRenovacion?:string|null};
export type LeadCredit={id:string;agencyId:string;cupo:number;consumido:number;available:number};
export type Agency={id:string;name:string;city:string;verified:boolean;claimed:boolean;phone?:string|null;verificationStatus?:string;instagram?:string|null;websiteLink?:string|null;freeLeadsRemaining?:number;slug?:string|null;subscriptionTier?:string|null;planLeadQuota?:number|null;leadsUsedCurrentPeriod?:number;subscriptionStartedAt?:string|null;availableCredit?:number;subscription?:Subscription|null;leadCredit?:LeadCredit|null};
export type Opportunity={id:number;property_id?:string;user_id?:string;event:string;created_at:string;context:Record<string,unknown>};
export type BuyerProfile={name:string;phone:string;email?:string;phoneVerified?:boolean;googleVerified?:boolean};
export type DemandSummary={sampleSize:number;topZones:{zone:string;count:number}[];topTypes:{type:string;count:number}[];topOperations:{operation:string;count:number}[];avgResultCount:number|null};
export type PendingAgency={id:string;name:string;city:string;phone?:string|null;claimed:boolean;instagram?:string|null;websiteLink?:string|null;verificationStatus:string;verificationPriority:number;verificationNotes?:string|null;verificationReviewedAt?:string|null};
export type ReviewQueueItem={property:Property;candidate:Property|null};

export type Session={token:string;user:{id:string;phone:string;role:Role;agency_id:string}};
export type Role='AGENTE'|'COMPRADOR';
