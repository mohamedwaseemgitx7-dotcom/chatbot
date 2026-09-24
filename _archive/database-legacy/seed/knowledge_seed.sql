-- Seed: Initial Agricultural Knowledge Baseline
INSERT INTO public.knowledge (id, crop, topic, subtopic, language, title, content, source)
VALUES
('rice_yellow_leaf_001', 'rice', 'yellow_leaf', 'nutrient_deficiency', 'english', 'Rice Yellow Leaf', 'Yellowing of rice leaves can be caused by nitrogen deficiency or water stress.', 'TNAU'),
('rice_yellow_leaf_ta_001', 'rice', 'yellow_leaf', 'nutrient_deficiency', 'tamil', 'நெல் இலை மஞ்சள் நிறமாதல்', 'நெல் இலை மஞ்சள் நிறமாக மாறுவதற்கு நைட்ரஜன் பற்றாக்குறை அல்லது நீர் மேலாண்மை காரணமாக இருக்கலாம்.', 'TNAU')
ON CONFLICT (id) DO NOTHING;
